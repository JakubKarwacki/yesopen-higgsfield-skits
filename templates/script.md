# TYTUŁ ROBOCZY (zdanie z planszy)

- **Status:** szkic do akceptacji. Bez akceptacji nie uruchamiamy maszyny GPU ani nie wydajemy kredytów na wideo.
- **Pomysł:** jedno zdanie o sytuacji z życia i o tym, gdzie jest żart. YesOpen pojawia się tylko jako puenta, nie jako prezentacja.
- **Długość:** ... s łącznie z planszą końcową; ... fps; ... klatek.
- **Język dialogu:** ...; **formaty zamówione przez użytkownika:** ... .
- **Wersja / data scenariusza i źródło akceptacji:** ... .
- **Tryb odsłuchu:** bieżący / odroczony wyraźnym poleceniem użytkownika; treść, data i zakres: ... .
- **Założenia:** brak / konkretna lista wymagająca rozstrzygnięcia przed produkcją.

## Wzór

[Tytuł filmu-wzoru](https://www.youtube.com/watch?v=...) z kanału ... (długość, wyświetlenia). Bierzemy z niego tylko mechanikę, własnymi słowami:

- forma (np. dwie osoby mówią do obiektywu na zmianę, cięcie co 1–2 s);
- silnik żartu (np. rozjazd między tym, co postać mówi, a tym, co widać);
- montaż (przybliżenia na akcent, ujęcia reakcji, żółte napisy po 2–4 słowa).

Nie kopiujemy kwestii, kadrów ani nazw z wzoru.

## Postacie

Obsadę piszemy razem ze scenariuszem: każda postać wynika z roli w żarcie, a z tej tabeli powstają `look`
w `lines.json` i źródło głosu. Postać lub głos z innego skeczu tylko wtedy, gdy scenariusz ją sprowadza z powrotem.

- **POSTAĆ 1:**
  - rola w żarcie (kim jest dla widza, co wie, czego nie wie);
  - wiek, wygląd, strój bez logo, rekwizyt;
  - miejsce (lokalny biznes, konkretne detale planu);
  - warianty potrzebne w ujęciach (poza, rekwizyt, strój, miejsce) — zgodne z tabelą ciągłości;
  - sposób mówienia, temperament i to, jak zmienia się w trakcie;
  - głos: jak powstaje z tej postaci (próbka z jej zdjęcia i roli), dowód uprawnienia, plik i SHA-256 w
    `voices/provenance.json`;
  - wybrane zdjęcie i powód wyboru względem scenariusza (po castingu).
- **POSTAĆ 2:** ...

## Scenariusz

| ID | Kto | Kwestia | Gra i ujęcie |
| --- | --- | --- | --- |
| U01 | POSTAĆ 1 | ... | ... |
| U02 | POSTAĆ 2 | ... | ... |
| ... | | | |
| plansza | plansza | YesOpen · zatwierdzone zdanie i opcjonalny adres | ... s |

Banery powiadomień, napisy i planszę nakładamy w montażu. Model wideo nie pisze tekstu na ekranie.

## Ciągłość każdego ujęcia — przed zdjęciami startowymi

Każde cięcie ma własny identyfikator. Rozdziel dialog dwóch osób na ujęcia, chyba że zaplanowano wspólny kadr.

| ID | START: kadr, pozycja, spojrzenie, dłonie i rekwizyty | AKCJA / DIALOG: kolejność | END: zakończone zdarzenie i dokładny stan końcowy | HOLD: czas na wybrzmienie po akcji | NEXT: ID i zgodny stan wejścia / rodzaj cięcia |
| --- | --- | --- | --- | --- | --- |
| U01 | ... | ... | ... | ... | U02: ... |

- Stałe planu: oś rozmowy, miejsca postaci, ubrania, światło, położenie i ręka trzymająca każdy rekwizyt.
- Stan postaci poza kadrem pozostaje ciągły; zmiany opisujemy jawnie.
- Każdy prompt generacyjny zawiera START, AKCJĘ, END i HOLD; zdjęcie startowe odpowiada temu ujęciu.
- Długość obejmuje pełną kwestię, zakończenie ruchu i reakcję. Potwierdzamy ją na nagranym dialogu.
- Przed montażem: obejrzyj ukończenie akcji, końcową klatkę i wejście następnego ujęcia.
- Nie tniemy w połowie słowa, podnoszenia przedmiotu ani wstawania. Brakujący finał wymaga poprawienia ujęcia.

## Co jest prawdą o produkcie

Każdą puentę o funkcji YesOpen sprawdzam w `business-card/messages/en/*.json` (strona i aplikacja):

| Puenta | Źródło (plik i fragment) |
| --- | --- |
| ... | ... |

Funkcje, których nie znalazłem, nie wchodzą do scenariusza: ...

## Decyzje

- ...

## Produkcja

Zostaw wariant silnika, którego używasz (`project.json` → `engine`).

Serwer GPU (`gpu`):

- **Zdjęcia startowe:** Z-Image ze wstępem o kadrze, 4 kandydatów na postać (`gpu_batches.py stills`); powracające postacie z `assets/cast/`.
- **Głos:** Chatterbox Multilingual V3 dla obsługiwanych języków, głos sklonowany z próbki w `voices/`; każda kwestia dwa razy, potem `fit_lines.py` sprawdza słowa i przycina.
- **Ujęcia z mową:** LTX-2.3 do gotowej kwestii, jedno ujęcie na kwestię; kadr się nie zmienia, telefon tyłem do kamery.
- **Montaż:** skrypty skilla (`make_edl.py`, `assemble.py`), wyłącznie zamówione formaty z `project.json`.
- **Szacunkowy koszt:** minuty GPU z `gpu_batches.py estimate` i czas całej sesji razy cena maszyny za godzinę; koniec pracy serwera zgodnie z bieżącą dyspozycją, pobraniem materiałów i sprawdzeniem wspólnej kolejki.

Higgsfield (`higgsfield`):

- **Zdjęcia startowe:** Soul 2, 9:16, 1080p, `batch_size` 4, `enhance_prompt: false`.
- **Ujęcia z mową:** Seedance 2.5 image-to-video, `generate_audio: true`, 720p; każda postać mówi swoje kwestie w 1–2 długich ujęciach, z pauzami na słuchanie.
- **Montaż:** skrypty skilla (`make_edl.py`, `assemble.py`), wyłącznie zamówione formaty z `project.json`.
- **Szacunkowy koszt:** suma z `hf-job cost` dla każdego ujęcia; stawka za sekundę zależy od rozdzielczości.

## Plan czasu po dopasowaniu głosu

| ID | Czas wejścia–wyjścia | Gotowy dialog (s) | Ruch / reakcja bez podwójnego liczenia (s) | HOLD (s) | Razem (klatki) |
| --- | --- | --- | --- | --- | --- |
| U01 | ... | ... | ... | ... | ... |
| plansza | ... | — | — | ... | ... |
| SUMA | ... | | | | ... |

Suma obejmuje planszę; czas liczymy z wybranych WAV i pełnych zakończeń ujęć. Tabela dialogu,
ciągłości i czasu używa tych samych ID. Tryb odroczonego odsłuchu nie oznacza `accepted`:
kontrole słuchowe pozostają `not_reviewed`; wyniki techniczne zapisujemy oddzielnie.

## Gotowość przed pełną partią

- Wersja kodu, modeli i konfiguracji: ...
- Język i wynik próbki audio → dopasowanie → napisy: ...
- Rzeczywisty czas dialogu: ...; dodatkowe ruchy i pauzy bez podwójnego liczenia: ...; plansza: ...; suma: ...
- Zgodność z zaakceptowaną długością / rozstrzygnięta zmiana: ...

| Próba (ID ujęcia) | Ryzyko: dialog / rekwizyt / ruch ciała | Wynik, wybrany plik i dowód obejrzenia końca | Poprawka / zgoda na pozostałą partię |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Wznawianie i zakończenie

- Checkpoint, ostatni potwierdzony etap, identyfikatory zadań: ...
- Wybrane wersje ujęć i granice montażu: ...
- Bieżąca dyspozycja infrastruktury: Stop / Delete / pozostawić; źródło i czas: ...
- Zasoby chronione, w tym dyski: ...
- Pobrane pliki i dowód kompletności: ...
- Rzeczywiste zadania blokujące zakończenie (puste po rozliczeniu): ...
- Wynik operacji dostawcy, czas, identyfikator instancji i dowód: ...
- Zachowane zasoby i możliwe dalsze opłaty: ...
