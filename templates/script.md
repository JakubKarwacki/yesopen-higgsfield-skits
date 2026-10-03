# TYTUŁ ROBOCZY (zdanie z planszy)

- **Status:** szkic do akceptacji. Bez akceptacji nie uruchamiamy maszyny GPU ani nie wydajemy kredytów na wideo.
- **Pomysł:** jedno zdanie o sytuacji z życia i o tym, gdzie jest żart. YesOpen pojawia się tylko jako puenta, nie jako prezentacja.
- **Długość:** około 45 s, pionowo 9:16, po angielsku (inne formaty robimy z tego samego montażu).

## Wzór

[Tytuł filmu-wzoru](https://www.youtube.com/watch?v=...) z kanału ... (długość, wyświetlenia). Bierzemy z niego tylko mechanikę, własnymi słowami:

- forma (np. dwie osoby mówią do obiektywu na zmianę, cięcie co 1–2 s);
- silnik żartu (np. rozjazd między tym, co postać mówi, a tym, co widać);
- montaż (przybliżenia na akcent, ujęcia reakcji, żółte napisy po 2–4 słowa).

Nie kopiujemy kwestii, kadrów ani nazw z wzoru.

## Postacie

- **POSTAĆ 1:**
  - wiek, wygląd, strój bez logo, rekwizyt;
  - miejsce (lokalny biznes, konkretne detale planu);
  - sposób mówienia i to, jak zmienia się w trakcie.
- **POSTAĆ 2:** ...

## Scenariusz

| # | Kto | Kwestia | Gra i ujęcie |
| --- | --- | --- | --- |
| 1 | POSTAĆ 1 | ... | ... |
| 2 | POSTAĆ 2 | ... | ... |
| ... | | | |
| N | plansza | YesOpen · zdanie z planszy · yesopens.com | 2,6 s |

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
- **Głos:** Chatterbox, głos sklonowany z próbki w `voices/`; każda kwestia dwa razy, potem `fit_lines.py` sprawdza słowa i przycina.
- **Ujęcia z mową:** LTX-2.3 do gotowej kwestii, jedno ujęcie na kwestię; kadr się nie zmienia, telefon tyłem do kamery.
- **Montaż:** skrypty skilla (`make_edl.py`, `assemble.py`), formaty 9:16, 4:5, 1:1, 16:9.
- **Szacunkowy koszt:** minuty GPU z `gpu_batches.py estimate` i czas całej sesji razy cena maszyny za godzinę; koniec pracy serwera zgodnie z bieżącą dyspozycją, pobraniem materiałów i sprawdzeniem wspólnej kolejki.

Higgsfield (`higgsfield`):

- **Zdjęcia startowe:** Soul 2, 9:16, 1080p, `batch_size` 4, `enhance_prompt: false`.
- **Ujęcia z mową:** Seedance 2.5 image-to-video, `generate_audio: true`, 720p; każda postać mówi swoje kwestie w 1–2 długich ujęciach, z pauzami na słuchanie.
- **Montaż:** skrypty skilla (`make_edl.py`, `assemble.py`), formaty 9:16, 4:5, 1:1, 16:9.
- **Szacunkowy koszt:** suma z `hf-job cost` dla każdego ujęcia; stawka za sekundę zależy od rozdzielczości.

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
