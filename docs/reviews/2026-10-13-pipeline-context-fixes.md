# Naprawy po audycie kontekstu pipeline’u

Stan: poprawki kodu i grafu wdrożone na instancji dev CPU. Pełna generacja
MiniMax i ocena obrazu/lipsyncu wymagają testów MVP na GPU.

Główny graf ma 34 nody. Generacyjne etapy rozwijają wspólne szablony API w
natywne nody ComfyUI podczas wykonania; mniejsza liczba nodów widocznych w
grafie nie oznacza usunięcia generatorów. Szablony pozostają w workflows/api.

| Ustalenie audytu | Zmiana |
|---|---|
| 1. Muzyka demo | Usunięta z produkcyjnego grafu. Generowanie wymaga jawnej specyfikacji muzyki; instrumentalny podkład nie przyjmuje tekstu piosenki. |
| 2. Obowiązkowa muzyka / brak BPM | Tryby wyłączenia, istniejącego pliku i generacji. Wybór istniejącego utworu zachowany; BPM i pozostałe parametry trafiają do metadanych. Długość wyliczana z EDL. |
| 3. Utrata parametrów ujęcia | Graf korzysta z map parametrów klienta API. Nadpisania per kwestia zachowane; prompt wejściowy, przygotowany graf i rzeczywiste teksty encoderów zapisane. |
| 4. Klatki i audio | Wspólne funkcje frame_grid z klienta. Audio dopełniane ciszą do czasu siatki, próba skrócenia zatwierdzonego audio odrzucana. |
| 5. Stary głos | FitLine przekazuje wyłącznie bieżący plik jako candidate. Checkpoint obejmuje audio i raport dopasowania. |
| 6. Wyłączenie napisów | Decyzja przechodzi przez EDL i argumenty montażu; fallback ASR nie włącza wyłączonych napisów. |
| 7. Zakres odsłuchu | Jawna lista identyfikatorów i zgodność tensorów z aktualnymi plikami. Zgoda obejmuje dokładnie odsłuchane kwestie. |
| 8. Stałe prompty Qwen/B-roll | Warianty scen korzystają z lines[].variants.<name>: jawny template, prompt, seed i parametry ujęcia. Brak specyfikacji zatrzymuje włączony wariant. |
| 9. MiniMax poza produkcją | H3 jest domyślny dla nowych projektów. h3-talk z MiniMaxH3AddGuide używa zatwierdzonego audio; wynik przechodzi do SaveTake, montażu i dostawy. Jawne starsze nadpisania modelu pozostają respektowane. |
| 10. Seed i obsada | Kandydaci generowani per postać z walidacją look. Ten sam seed trafia do samplera, nazwy pliku i metadanych zadania. |
| 11. Wymuszony upscale/FILM | Domyślnie wyłączone. Postprocess z projektu/per kwestia wymaga enabled i jawnego multiplier. |
| 12. Cache bez transkrypcji | Checkpoint obejmuje MP4 oraz words.json. Brak/zmiana transkrypcji wznawia inspekcję, jeśli MP4 i specyfikacja są aktualne. Zmiana MP4 wymaga generacji. |
| 13. Narzucone pauzy i próg ASR | Konfiguracja fit per projekt/kwestia oraz CLI. Domyślnie bez skracania pauz, min_ratio=1.0; użyta polityka i hash źródła zapisane w raporcie. |
| 14. Rozdzielone manifesty / formaty | SaveTake aktualizuje project.takes. Walidacja selekcji i cutawayów, jawne edit.omitted_lines dla pominiętych kwestii. Render, QA i dostawa używają project.formats. |

## Konfiguracja

Nowe projekty mają muzykę wyłączoną i napisy włączone. Zmiany decyzji zapisuje
się w project.json, a następnie ponownie uruchamia etapy montażu po bramkach.
Podgląd zachowuje stare niezapisane karty; nowy graf otwarty jest osobno.

```json
{
  "captions": {"enabled": false},
  "music": {
    "enabled": true,
    "mode": "generate",
    "instrumental": true,
    "tags": "light playful piano, understated comedy",
    "bpm": 90,
    "seed": 42,
    "keyscale": "C major",
    "timesignature": "4",
    "language": "en",
    "tail": 10
  },
  "formats": ["9:16", "1:1"]
}
```

Przykład jawnej specyfikacji opcjonalnej edycji w konkretnej kwestii lines.json:

```json
{
  "variants": {
    "pose": {
      "template": "still-edit",
      "set": {
        "image": "stills/char1.png",
        "prompt": "The same person turns toward the doorway, keeping the approved clothing and room unchanged.",
        "seed": 81,
        "fast": true
      }
    }
  }
}
```

Węzeł Wariant sceny pozostaje wyłączony do świadomego uruchomienia. Wygenerowany
wariant nadal wymaga wyboru przez operatora, zanim zostanie użyty w montażu.

## Weryfikacja

- test_pipeline_contracts: muzyka, decyzje montażu, zgodność reguł klatek API/graf,
  aktualny kandydat TTS, zachowanie pauz, domyślny H3 i zakres formatów.
- test_pipeline_nodes w obrazie ComfyUI na dev: 16 testów, wszystkie przeszły;
  w tym natywne rozwinięcie H3, guide audio, opcjonalny upscale/FILM, seed
  obsady, dokładny zakres odsłuchu i wznowienie transkrypcji.
- Pełny zestaw regresji klienta/skryptów: 142 testy, wynik OK,
  10 pominięć zależnych od środowiska. Cztery z tych
  pominiętych testów rozwijania grafów wykonano osobno w ComfyUI na dev.
- Zapisany główny graf przyjęty przez API ComfyUI bez błędów nodów. Przebieg
  z zamkniętymi bramkami zakończył się success, bez generowania mediów.
- Suma SHA-256 grafu na dev zgodna z repozytorium. Potwierdzono cpu-d3,
  2vcpu-8gb i przypięcie dysku yesopen-dev-disk-jakub-kacper.

Żaden test nie generował wideo ani muzyki na GPU. Nie zmieniano projektu
produkcyjnego pracowników ani ich instancji.
