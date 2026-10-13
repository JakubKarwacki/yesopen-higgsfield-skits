# Silniki wideo: MiniMax i testy Wan 3.0

Decyzja projektu z 13 października 2026: głównym silnikiem wideo jest lokalnie
hostowany **MiniMax H3**. Alternatywą do zbadania jest **Wan 3.0 hostowany lokalnie**.

## MiniMax H3 — główny wybór

- Dialog: `h3-talk`, czyli wybrany still oraz gotowe, zatwierdzone audio.
- Ujęcia z natywnym dźwiękiem: `h3-i2v` lub `h3-r2v`, z jawną specyfikacją audio.
- W `lines.json` ustawiaj `take.model: "h3"`. Dla batcha używaj
  `gpu_batches.py takes --model h3`; sprawdź nadpisania `lines[].model`.
- Prompt opisuje START, kolejność akcji, wypowiedź, END i HOLD; dla H3 używa
  `<Picture 1>`, `SHOT 1` oraz opisu audio.

**Stan wdrożenia:** nowe projekty domyślnie wybierają H3. Główny graf korzysta
z tego samego szablonu `h3-talk` i reguł klatek co klient API, przekazuje
zatwierdzone audio i zapisuje wynik do montażu. Jawne nadpisania modelu w
istniejących projektach pozostają respektowane. Testy logiki przeszły; testy
jakości pełnej generacji na GPU pozostają do wykonania.

Warunki korzystania określa aktualna
[licencja MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE).
Standardowy zakres terytorialny wyłącza UE, UK, Koreę Południową i USA;
dla wdrożenia w takim zakresie potrzebna jest odpowiednia licencja od MiniMax.
Wybór silnika nie oznacza potwierdzenia uzyskania tej licencji.
[Oficjalna karta modelu](https://huggingface.co/MiniMaxAI/MiniMax-H3) wskazuje
formularz dotyczący tych regionów.

## Wan 3.0 — alternatywa do testów lokalnych

Cel to uruchomienie na własnej instancji GPU. Pierwszy etap: potwierdzić oficjalne
wagi, licencję na lokalne wdrożenie oraz referencyjną implementację.

Stan sprawdzenia 13 października 2026: oficjalna
[dokumentacja Alibaba](https://www.alibabacloud.com/help/en/model-studio/wan3-0-video)
opisuje Wan 3.0 jako usługę Alibaba Cloud Model Studio. Przejrzane
[repozytoria Wan](https://github.com/Wan-Video) i
[hub Wan-AI](https://huggingface.co/Wan-AI) nie potwierdziły dostępnego pakietu
Wan 3.0 do lokalnej inferencji. Obsługa API ani sam model card nie potwierdzają
możliwości lokalnego hostingu. Status: **weryfikacja dostępności przed testami**.

Po potwierdzeniu lokalnego wydania:

1. Przypiąć wersję wag, kodu i licencji; ustalić VRAM i zależności.
2. Zbudować adapter wspólnego kontraktu: referencje, audio, prompt, czas, seed,
   wynik i pochodzenie plików.
3. Porównać z H3 te same ujęcia: tożsamość, lipsync, tekst, rekwizyty, zakończenie
   ruchu, czas i koszt GPU, pamięć oraz skuteczność ponowień.
4. Testować na dysku dev; przejść do produkcji po wynikach MVP.

Obecne `two-shot` oparte na starszym modelu Wan nie jest integracją Wan 3.0.
