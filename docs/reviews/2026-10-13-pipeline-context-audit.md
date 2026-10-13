# Audyt nodów, stałych wartości i kontekstu pipeline’u

> Ustalenia poniżej zachowują stan sprzed poprawek. Implementacja napraw wszystkich
> 14 punktów: [raport napraw](2026-10-13-pipeline-context-fixes.md). Testy jakości GPU pozostają w MVP.

> Zapis historyczny implementacji lub wykonanej produkcji. Od 13 października 2026 głównym wyborem projektu jest MiniMax H3, a Wan 3.0 hostowany lokalnie jest alternatywą do testów. Nazwy poprzednich modeli i wyniki poniżej opisują stan z daty raportu; bieżące instrukcje i status migracji: references/video-models.md.

Data: 13 października 2026. Zakres: `yesopen-skit-pipeline`, 81 nodów głównych,
7 podgrafów, nody `yesopen_pipeline`, generator grafu i skrypty przygotowujące
audio, prompty oraz montaż. Sprawdzono również zapisany graf na uruchomionym
serwerze oraz definicje i kod wskazanych nodów ComfyUI 0.35.0.

To analiza kodu i połączeń. Nie uruchamiano generacji, renderu ani testów modeli
na GPU. Skutki dotyczące jakości obrazu, śpiewu i synchronizacji wymagają później
prób na GPU; opisane utraty ustawień i błędy logiki wynikają bezpośrednio z kodu.

Graf zapisany na serwerze ma tę samą liczbę nodów i podgrafów. Różnice wobec
repozytorium obejmują normalizację widgetów przez frontend i zmianę części
identyfikatorów wewnętrznych. Identyfikatory głównych nodów podane niżej są
wspólne dla obu wersji. Samo porównanie plików bajt po bajcie nie wystarcza.

Priorytety: **P1** — błędna treść, utrata decyzji lub blokada produkcji;
**P2** — niespójny kontrakt, ograniczenie kontekstu albo istotne ryzyko jakości.

## Najważniejsze ustalenia

### 1. P1 — aktywna muzyka zawiera przykładową piosenkę z wokalem

**Nody:** główny `1045` (`TextEncodeAceStepAudio1.5`), `1038` (długość),
`1046` (seed), `1067` (`YesOpenSaveMusic`).

Gałąź ACE-Step jest aktywna. W `tags` nadal są rap, kobiece wokale i stylistyka
„Late Night Trap”; `lyrics` zawiera zwrotki i refren o ComfyUI. Stałe to również
95 BPM, 120 sekund, język `en`, tonacja E minor i seed 0. Żadne z tych pól
nie pochodzi ze scenariusza ani z konfiguracji muzyki projektu.

Generator otrzymuje zatem polecenie stworzenia piosenki, mimo że notatka sekcji
obiecuje podkład instrumentalny. Taki materiał może konkurować z dialogiem,
wprowadzić obcy tekst i zmienić ton scenki. 120 sekund nie wynika z czasu montażu;
przy dłuższym projekcie podkład może być za krótki.

**Źródła:** `gpu/workflows/pipeline/yesopen-skit-pipeline.json`, node 1045;
`gpu/tools/build_pipeline_graph.py`, `STAGES`, `apply_node_defaults`.

**Naprawa:** jawna specyfikacja muzyki projektu; instrumentalność, tekst,
język, tempo, seed i długość muszą mieć jedno źródło. Długość wyliczać z montażu
z zapasem. Gałąź włączać dopiero po decyzji o muzyce.

### 2. P1 — muzyka jest obowiązkowa, a zapis nie przekazuje wymaganego BPM

**Nody:** `1067` (`YesOpenSaveMusic`), `1068` (`YesOpenJoinProduction`).

`JoinProduction` wymaga ścieżki muzyki. `SaveMusic` zapisuje zawsze
`music/<name>.flac` i ustawia `project.json → music.file`, także gdy projekt
pierwotnie nie miał muzyki lub wskazywał wybrany podkład z innego źródła.
Nie zapisuje BPM użytego do generacji.

`scripts/music.py:166` odmawia montażu, jeśli blok `music` nie ma `bpm`.
Szablon `project.json` oraz przykład `gym-breakup-gpu` w repo nie mają bloku
muzyki. Dodanie przez node samego `file` tworzy konfigurację niewystarczającą
do montażu. Jeśli istnieje wcześniejsze BPM, zostaje ono zachowane mimo
generowania w stałym tempie 95 BPM; wyszukiwanie tempa działa w zakresie ±3%.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:373` i `:476`;
`scripts/music.py:159`; `templates/project.json`.

**Naprawa:** obsłużyć montaż bez muzyki, wybór istniejącego pliku i generowanie
nowej muzyki jako jawne decyzje. Przekazywać metadane faktycznie użytego utworu,
w tym BPM; nie nadpisywać wyboru podkładu samym uruchomieniem grafu.

### 3. P1 — ustawienia ujęcia z projektu są gubione przed LTX

**Nody:** `1061` (`YesOpenFitLine`), `1012` (LTX-2.3).

`gpu_batches.py` zapisuje `enhance_prompt`, `cfg_first` i `negative_prompt`
z `take` lub konkretnej kwestii. `FitLine` odczytuje zadanie, ale zwraca jedynie
audio, prompt, czas, seed, still, flagę i raport. Te trzy ustawienia nie mają
dalszej drogi do LTX.

Podgraf używa więc własnych wartości: pierwsze CFG = 1, stały negative prompt
oraz `prompt_enhance=true`. Co szczególnie istotne, klient API ma domyślnie
`enhance_prompt=false`, z uzasadnieniem, że prompty scenek są już kompletne.
W grafie ekranowym prompt jest ponownie przepisywany przez Gemma
(`TextGenerateLTX2Prompt`) z dodatkową LoRA. Zlecenie zachowania dokładnego
promptu w projekcie nie wyłącza tego etapu.

**Źródła:** `scripts/gpu_batches.py:290`;
`gpu/server/yesopen_pipeline/__init__.py:299` i `:332`;
`gpu/workflows/params/talk.json:76`; podgraf LTX-2.3, nody 314, 315, 346 i 349.

**Naprawa:** przekazywać pełną specyfikację ujęcia i wszystkie wspierane
parametry. Ujednolicić zachowanie grafu i klienta API. Rejestrować zarówno
prompt wejściowy, jak i ostateczny prompt użyty do generacji.

### 4. P1 — ekranowy LTX omija przygotowanie długości klatek i audio

**Node:** `1012`; wewnątrz LTX-2.3 nody 329, 302, 332, 328 i 326.

Klient `gpu.py` zaokrągla długość w górę do siatki LTX `8n+1` i dopełnia audio
ciszą do odpowiedniego czasu. Graf ekranowy przekazuje surowe `seconds` z batcha,
wylicza `a * b + 1` i korzysta z całkowitoliczbowego wyjścia wyrażenia.
`EmptyLTXVLatentVideo` wylicza wymiar czasowy przez dzielenie całkowite.

Dla 5,27 s i 24 fps wyrażenie daje po konwersji 127 klatek, a wymiar latentów
odpowiada siatce 121 klatek. Przygotowanie w kliencie API wybrałoby 129 klatek.
Graf może więc skrócić zamierzony ogon ujęcia; przy małym ogonie ryzyko obejmuje
końcówkę wypowiedzi.

`TrimAudioDuration` tylko przycina istniejące audio. Kod zainstalowanego noda
potwierdza, że nie dodaje ciszy, gdy żądany czas jest dłuższy. Obietnica
`tail` ze scenariusza nie daje przez ten node audio dopełnionego do czasu filmu.
Nie potwierdzono na GPU, jak konkretny model zachowa się przy tej rozbieżności.

**Źródła:** `gpu/client/gpu.py:164`, `:230`, `:382`;
podgraf LTX-2.3; zainstalowane `nodes_math.py`, `nodes_lt.py`, `nodes_audio.py`.

**Naprawa:** używać wspólnego przygotowania zadania w API i grafie: jawna liczba
klatek, rzeczywisty czas oraz dopełnione audio. Sprawdzić też analogiczne
wyrażenie długości w opcjonalnym LTX-2.5.

### 5. P1 — ponowne dopasowanie głosu może wybrać stare wykonanie

**Nody:** `1059` (`YesOpenLine`), `1061` (`YesOpenFitLine`).

`FitLine` zapisuje nowy plik audio wybranego seeda, po czym uruchamia
`fit_lines.py`. Skrypt przegląda jednak wszystkie pliki `lXX-s*.audio.flac`
i wybiera najlepiej pasujący tekstowo. Nie ogranicza kandydatów do aktualnej
wersji głosu, ekspresji i parametrów TTS.

Po zmianie próbki głosu lub sposobu mówienia stary plik innego seeda może
ponownie wygrać. Ostatecznie powstanie audio sprzed zmiany, a nowy checkpoint
zostanie zapisany z sygnaturą aktualnej konfiguracji. Samo unieważnienie cache
nie zapobiega temu wyborowi.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:317`;
`scripts/fit_lines.py:148`; `gpu/server/yesopen_pipeline/runtime.py:46`.

**Naprawa:** kandydatów wiązać z rewizją tekstu, głosu i parametrów TTS;
przekazywać konkretną listę dopuszczonych plików oraz przechowywać pochodzenie
wybranego wykonania.

### 6. P1 — wyłączenie napisów może uruchomić automatyczne napisy

**Nody:** `1072`, `1076` (`YesOpenAssemble`).

`make_edl.py` respektuje `captions.enabled=false` i tworzy pustą listę słów.
Node montażu nie przekazuje `--no-captions`. `assemble.py` ma napisy domyślnie
włączone i przy pustej liście słów uruchamia Whisper jako fallback.
W efekcie świadome wyłączenie napisów zostaje potraktowane jako brak danych
do napisów, które należy wygenerować.

**Źródła:** `scripts/make_edl.py:84`; `scripts/assemble.py:58` i `:103`;
`gpu/server/yesopen_pipeline/__init__.py:562`.

**Naprawa:** zachować jawną decyzję `captions.enabled` w EDL i nodzie montażu.
Fallback ASR może działać tylko wtedy, gdy napisy są włączone. Zastosować
analogiczny kontrakt dla muzyki.

### 7. P1 — zatwierdzenie odsłuchu ma szerszy zakres niż wybrane audio

**Node:** `1062` (`YesOpenVoiceApproval`).

Node otrzymuje wybrane audio, lecz zapisuje zatwierdzenie dla wszystkich
`lines/*.wav` w projekcie. Wybór tylko `l01` nie ogranicza zatwierdzenia do `l01`;
obejmuje również inne kwestie i pliki dopełnione `*-pad.wav`, jeśli istnieją.
Z kolei zmiana niepowiązanego pliku może unieważnić odsłuch wybranego materiału.

Sygnatura zatwierdzenia opisuje pliki, ale nie ich świadomie wybraną listę.
To nie jest zgodność zakresu materiału przedstawionego operatorowi z zakresem
zatwierdzenia.

**Źródło:** `gpu/server/yesopen_pipeline/__init__.py:353`–`:370`.

**Naprawa:** przekazywać identyfikatory kwestii i pochodzenie plików wraz z audio;
zatwierdzać dokładnie tę listę oraz jej rewizję.

## Pozostałe niespójności

### 8. P2 — Qwen i B-roll nie mają promptu konkretnego ujęcia

**Nody:** `1020` (Qwen), `1031` (LTX-2.5).

Qwen dostaje właściwy still, ale polecenie edycji jest stałe: telefon tyłem do
kamery i uśmiech. LTX-2.5 dostaje stałą reakcję na telefon oraz stałe 5 sekund.
Prompty nie pochodzą z `action`, `prompt`, referencji ani opisu B-rollu dla danej
kwestii. Obie gałęzie są wyciszone, więc ryzyko pojawia się po ich włączeniu.

**Źródła:** `gpu/tools/build_pipeline_graph.py:82`, `:88`, `LINKS`;
główny graf, nody 1020 i 1031.

**Naprawa:** osobna specyfikacja każdego ujęcia i wariantu edycji, przetwarzana
przez planowany konwerter scenariusza na prompty.

### 9. P2 — MiniMax w grafie nie jest alternatywą produkcyjnego lip syncu

**Node:** `1016` (MiniMax H3), gałąź wyciszona.

Graf korzysta z wariantu image-to-video z natywnym audio. Nie przekazuje mu
zatwierdzonego nagrania; ma stały prompt, a jego wynik trafia do osobnego
podglądu zamiast do głównej ścieżki zapisu i montażu. Jednocześnie `FitLine`
odrzuca batch z szablonem innym niż `talk`, więc wybranie `model: h3` w projekcie
zatrzymuje produkcję wcześniej. Samo odciszenie MiniMax nie przełącza silnika.

Repo ma odrębny szablon API `h3-talk` z wejściowym audio, którego ta gałąź
ekranowa nie wykorzystuje.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:329`;
`gpu/tools/build_pipeline_graph.py`, `LINKS`; `gpu/workflows/api/h3-talk.json`.

**Naprawa:** jawny wybór silnika i wspólny kontrakt `still + audio + prompt +
parametry → take`, z zapisem rezultatu do projektu.

### 10. P2 — seed zapisany przy stillu nie jest seedem generatora stilla

**Nody:** `1004` (Z-Image), `YesOpenSaveStill` z gałęzi `z`.

`YesOpenLine.seed` trafia do noda zapisującego still i nazwy pliku, ale nie
do wejścia `seed` Z-Image. Podgraf korzysta z własnego seeda i kontrolki
randomizacji. Nazwa `still-<who>-<seed>` może więc sugerować odtwarzalność,
której nie opisuje rzeczywistego zadania.

Gałąź działa też na liście kwestii, a nie unikalnych postaci. `look` jest
zwracane jako pusty tekst, jeśli postać go nie ma; nie ma w tym miejscu
walidacji. W przykładzie `gym-breakup-gpu` postacie mają wybrane stille, ale
nie mają `look`.

**Źródła:** `gpu/tools/build_pipeline_graph.py:314`–`:321`;
`gpu/server/yesopen_pipeline/__init__.py:272`;
podgraf Z-Image, wejście `seed` i KSampler.

**Naprawa:** generować kandydatów obsady według postaci, z walidacją promptu
oraz jednym seedem przekazanym do generatora i metadanych zapisu.

### 11. P2 — upscale i interpolacja są obowiązkowe mimo opisu opcjonalności

**Nody:** `1022` (SeedVR2), `1035` (FILM).

Produkcja zawsze przechodzi przez oba podgrafy. SeedVR2 ma mnożnik 2, mimo
notatki obiecującej 704×1280 → 1056×1920, czyli ×1,5. Dla wejścia 704×1280
ustawiony mnożnik oznacza 1408×2560. FILM domyślnie interpoluje ×2 i mnoży FPS.
Nie ma bramki pominięcia całych etapów, mimo opisu „gdy ruch szarpie”.

**Źródła:** `gpu/tools/build_pipeline_graph.py`, `STAGES` i `LINKS`;
podgraf SeedVR2, node 57; podgraf FILM.

**Naprawa:** ustalić docelową rozdzielczość i politykę FPS z projektu oraz
umożliwić świadome pominięcie przetwarzania. Sama konwersja 24 → 48 → 30 fps
nie jest dowodem błędu synchronizacji; istotne są obecna wymuszona ścieżka,
rozbieżny opis i koszt przetwarzania.

### 12. P2 — cache gotowego ujęcia nie obejmuje transkrypcji wymaganej dalej

**Node:** `1065` (`YesOpenSaveTake`).

Checkpoint `take/<id>` przechowuje hash wyłącznie MP4. Przy wznowieniu node
może pominąć `inspect_take.py`, nawet jeśli `.video.words.json` usunięto lub
zmieniono. Montaż potrzebuje tego pliku, a `require_takes` sprawdza jego
obecność, nie zgodność z aktualnym MP4.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:441`–`:448`;
`gpu/server/yesopen_pipeline/runtime.py:91`.

**Naprawa:** checkpoint materiału powinien obejmować MP4, transkrypcję i jej
powiązanie z hashem wideo. Brak metadanych powinien wznowić inspekcję.

### 13. P2 — dopasowanie audio narzuca rytm i tolerancję tekstu

`FitLine` nie przekazuje ustawień dopasowania. `fit_lines.py` zawsze stosuje
domyślne 0,3 s ciszy przed wypowiedzią, 0,12 s po niej i skracanie przerw
wewnątrz wypowiedzi do 0,75 s. Próg zgodności tekstu wynosi 0,9.
To może skrócić celową pauzę komediową lub zaakceptować rozbieżność tekstową.
Późniejsze QA nie cofa decyzji o zmianie rytmu wykonania.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:321`;
`scripts/fit_lines.py:112`, `:117`, `:176`, `:203`.

**Naprawa:** konfiguracja dopasowania per projekt i per kwestia, z jawną
polityką zachowania pauz. Rozdzielić próg ASR od zatwierdzenia przez operatora.

### 14. P2 — dane scenariusza i montażu mają rozdzielone źródła prawdy

Produkcja czyta postacie i kwestie z `lines.json`, natomiast `make_edl.py`
bierze ścieżki ujęć z `project.json.takes` i selekcję z `edit/cuts.json`.
`SaveTake` zapisuje stałą ścieżkę `takes/<id><suffix>.video.mp4`, ale nie
aktualizuje mapy `project.json.takes`. Dodanie kwestii albo wybranie wariantu
pliku nie aktualizuje automatycznie montażu.

`FORMATS` w nodach jest stałą listą czterech formatów; pole `project.formats`
nie wybiera zakresu renderu, QA i dostawy. To zgodne z obecnym założeniem
czterech wersji, ale nie z zachowaniem sugerowanym przez konfigurowalne pole.

**Źródła:** `gpu/server/yesopen_pipeline/__init__.py:28`, `:445`, `:608`;
`scripts/make_edl.py:32`; `templates/project.json`.

**Naprawa:** walidować spójność całej specyfikacji przed generacją i aktualizować
manifest materiałów po zapisie. Zakres formatów pobierać z tego samego planu.

## Co nie jest potwierdzonym błędem

- Przykładowy tekst o Kasi i widget `Polish (pl)` w Chatterbox są nadpisywane
  połączeniami z `YesOpenLine`. Ich obecność w JSON nie dowodzi, że głos będzie
  po polsku lub wypowie ten tekst.
- Domyślny prompt Z-Image jest nadpisywany przez `characters.<who>.look`.
  Realnym problemem jest brak walidacji pustego `look`, seed i generowanie
  według kwestii, nie sam tekst przykładu.
- Przykładowy prompt Vaporwave wewnątrz MiniMax jest nadpisywany wejściem
  podgrafu. Realnym problemem pozostaje stały prompt na poziomie głównym
  i użycie innego wariantu noda niż audio-conditioned `h3-talk`.
- W tym grafie **Qwen nie komponuje scenariusza**. Qwen służy m.in. do edycji
  obrazu i jako encoder; przepisywanie promptu LTX wykonuje Gemma. Scenariusz
  i analiza referencji powstają poza grafem. Punkt TODO o Gemini powinien
  wyraźnie rozróżnić scenarzystę, konwerter promptów i edytor referencji.
- `project.reference` nie jest wejściem generatorów w tym grafie. Kontekst
  referencji musi obecnie zostać przepisany do `look`, promptów i scenariusza
  przez operatora/agenta. Przekazanie samego URL do `project.json` nie zmienia
  generowanego materiału.

## Zalecana kolejność poprawek

1. Usunąć treści demo z aktywnej muzyki i naprawić opcjonalność oraz metadane
   podkładu; zachować decyzję o napisach.
2. Ujednolicić kontrakt zadania generacyjnego między ekranowym grafem i API:
   prompt, parametry LTX, klatki, audio, seed, wybrany silnik i pochodzenie.
3. Naprawić wybór wykonania TTS, zakres odsłuchu oraz kompletność checkpointów.
4. Zasilać opcjonalne ujęcia i edycje specyfikacją konkretnej sceny; poprawić
   obsadę, metadane seedów i spójność manifestu z montażem.
5. Dopiero potem przeprowadzić porównawcze testy MVP na GPU dla dialogu,
   pauz, lipsyncu, muzyki i braku napisów, z kontrolą rzeczywistych promptów.
