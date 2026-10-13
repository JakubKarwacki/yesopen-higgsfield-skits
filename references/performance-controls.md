# Kontrola jakości ujęć MiniMax H3

Główny silnik i stan migracji: [video-models.md](video-models.md).

Każde zadanie zawiera ID ujęcia, wybrany still, zatwierdzone audio, prompt H3,
czas, seed, profil jakości i wersję modeli. Zapisuj wartości faktycznie użyte.

Wspierane ustawienia batcha: `take.model: "h3"`, `take.h3_template`,
`lines[].h3_prompt`, `tail`, `silence_before`, `seconds`, `seed`, `take.fast`
oraz `take.megapixels`. Sprawdź nadpisania modelu per kwestia i kontrakt
`gpu/workflows/params/h3-talk.json`; parametry poprzedniego silnika nie stają się
automatycznie parametrami H3.

Przed pełną partią porównaj zwykły profil z turbo na tych samych wejściach.
Oceń dialog, pauzę komediową, lipsync, tożsamość, rekwizyty, zakończenie akcji
i HOLD. Zapisz czas GPU, VRAM, rzeczywiste prompty i wybrane pliki.
Nie przenoś wcześniejszych benchmarków na MiniMax.

Wan 3.0 podlega tym samym próbom po potwierdzeniu oficjalnego lokalnego wydania.
Historia wcześniejszych eksperymentów: `docs/archive/pre-minimax/performance-controls.md`.
