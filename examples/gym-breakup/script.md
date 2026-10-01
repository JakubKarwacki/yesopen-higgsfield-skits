# It's not you. It's your invoices.

- **Status:** zaakceptowany przez Marcina 2026-10-01, w produkcji. Ujęcia generuje Seedance 2.5 w 720p.
- **Pomysł:** właściciel siłowni zrywa ze swoją agencją marketingową. Agencja straszy pytaniami „a kto będzie…?”, a on za każdym razem udaje, że nie wie. Wtedy jego telefon dzwoni powiadomieniem, które odpowiada na to pytanie. Agencja zaczyna podejrzewać, że ma kogoś innego. Funkcje YesOpen pojawiają się tylko jako puenty, a nie jako prezentacja.
- **Długość:** około 45 s, pionowo 9:16, po angielsku.

## Wzór

„How to breakup with your girlfriend #shorts” z kanału Content Machine (49 s, 10,2 mln wyświetleń). Bierzemy z niego:

- obie postacie mówią prosto do obiektywu, na zmianę, z cięciem co 1–2 s;
- przybliżenia dla akcentu i krótkie ujęcia reakcji;
- żółte napisy po 2–4 słowa;
- udawane oburzenie oraz finał, w którym jedna strona wychodzi, a druga protestuje na pokaz, po czym się cieszy.

Link: https://www.youtube.com/watch?v=NvKrK5S0yS4. Analiza własnymi słowami: `reference/analysis.md`. Klatki i transkrypcja wzoru zostały na komputerze, poza repozytorium.

## Postacie

- **Właściciel (OWNER):**
  - około 38 lat, wysportowany, krótka broda, czarny T-shirt, ręcznik na ramieniu;
  - stoi w swojej małej siłowni przy hantlach, z telefonem w ręce;
  - mówi spokojnie i udaje bezradność coraz mniej przekonująco.
- **Agencja (AGENCY):**
  - account managerka około 30 lat, granatowa marynarka, czarny segregator, mrożona latte;
  - stoi przy recepcji tej samej siłowni;
  - pewna siebie, potem urażona, na końcu wściekła.

## Scenariusz

| # | Kto | Kwestia | Gra i ujęcie |
| --- | --- | --- | --- |
| 1 | OWNER | Hey… I think we should break up. | poważnie, trochę nerwowo |
| 2 | AGENCY | You're breaking up… with your marketing agency? | szok, przybliżenie |
| 3 | OWNER | It's not you. It's your invoices. | spokojnie, ze współczuciem |
| 4 | AGENCY | …Wow. | urażona, mruga |
| 5 | AGENCY | Fine. But who's going to answer all your questions? | odzyskuje pewność, grozi |
| 6 | OWNER | I don't know… | udaje zmartwienie. **DING**, baner: *YesOpen: Answered. Anything else?* Odwraca telefon ekranem w dół |
| 7 | AGENCY | Who's going to reply to your reviews? | |
| 8 | OWNER | No idea. | **DING**, baner: *YesOpen: 12 reviews answered*. Kaszle |
| 9 | AGENCY | Who's going to post on your Instagram? | zerka na jego telefon |
| 10 | OWNER | Not a clue. | **DING**, baner: *YesOpen: Your post is live on Instagram and Facebook*. Gwiżdże w bok |
| 11 | AGENCY | Who's going to get you to the top of Google Maps? | ostatnia karta |
| 12 | OWNER | Honestly? Absolutely no idea. | pije shake'a. **DING DING**, baner: *YesOpen: You're #1 for "gym near me"*. Nie ukrywa uśmiechu |
| 13 | AGENCY | Wait… are you seeing someone else? | mruży oczy, przybliżenie |
| 14 | OWNER | What? …What? No. | udaje urażonego, mocne przybliżenie |
| 15 | AGENCY | Then who keeps texting you? | |
| 16 | OWNER | It's… just an app. | zawstydzony, pokazuje telefon |
| 17 | AGENCY | You're leaving us… for an app?! | krzyk, przybliżenie |
| 18 | OWNER | It replies at 2 a.m. You reply in five business days. | wzrusza ramionami |
| 19 | AGENCY | Fine. You'll come crawling back. Don't even think about calling me. | wskazuje palcem, nachyla się do kamery, wychodzi |
| 20 | OWNER | What? Babe, no! Come back! | udawana rozpacz |
| 21 | OWNER | (cisza) | pauza, potem radość: głowa w tył, ręce szeroko. **DING**, patrzy w telefon i szepcze „Hey, you.” |
| 22 | plansza | YesOpen · It's not you. It's your invoices. · yesopens.com | 2,6 s |

Banery powiadomień nakładamy w montażu, więc tekst będzie dokładny. Model wideo nie pisze tekstu na ekranie.

## Co jest prawdą o produkcie

Każdą puentę sprawdziłem w treściach strony YesOpen (`business-card/messages/en/marketing.json`) i aplikacji (`app.json`, `nav.json`):

| Puenta | Źródło |
| --- | --- |
| Odpowiedzi na pytania | agent: „I can reply to reviews, prepare a post and help improve your profile” |
| Odpowiedzi na opinie | „AI replies to every review, in your voice” |
| Instagram i Facebook | publikacja kampanii przez Meta |
| Pozycja w Mapach | „Be the #1 business on Google Maps”, „Daily Google Maps ranking tracking” |
| „Replies at 2 a.m.” | „AI runs your Google profile 24/7”, „even while you're closed” |

Promocji w lokalnych artykułach nie znalazłem ani w kodzie, ani w designach. Dlatego nie ma jej w scenariuszu. Jeśli to istniejąca funkcja, dopiszę piąte pytanie: „Who's going to get you into the local news?”.

## Decyzje

- **Agencja:** account managerka.
- **Zdanie na planszy:** „It's not you. It's your invoices.”.
- **Liczba pytań:** cztery.

## Produkcja

- **Zdjęcia startowe:** Higgsfield Soul 2, 9:16, 1080p. Wybrane kadry są w `stills/picked.json`.
- **Wideo z mową i ruchem ust:** Seedance 2.5 image-to-video, `generate_audio: true`, 720p. Na 1080p nie starczyło środków.
  - Każda postać nagrywa swoje kwestie w dwóch dłuższych ujęciach, żeby głos był ten sam.
  - Montaż przeplata kwestie, a pauzy służą jako ujęcia reakcji.
- **Montaż:** ffmpeg, cięcia po znacznikach czasu z Whispera, przybliżenia, żółte napisy, banery, dźwięk powiadomienia, plansza w kolorach marki.

## Po produkcji

- **Gotowe:** 2026-10-01 o 20:09. Master 9:16, 1080×1920, 73,5 s (70,9 s scenki i 2,6 s planszy), −14,2 LUFS, true peak −1,4 dBTP.
- **Zmiany względem scenariusza:**
  - film trwa 73,5 s zamiast około 45 s, bo zostały wszystkie 21 kwestii, a pauzy z ujęć stały się reakcjami;
  - teksty banerów w montażu: „Answered your question. Anything else?”, „12 new reviews answered”, „Your post is live on Instagram and Facebook” i „You're #1 for “gym near me””;
  - przy „It's… just an app.” właściciel pokazuje tył telefonu zamiast ekranu, co jest bezpieczniejsze, bo nie ma wygenerowanego tekstu.
- **Pliki:**
  - `final/its-not-you-its-your-invoices-9x16.mp4` (master);
  - `final/its-not-you-its-your-invoices-9x16-share.mp4` (24 MB);
  - `final/web/` (wszystkie cztery formaty i plakaty).
- **Pełny przebieg produkcji:** `references/case-study-gym-breakup.md` w skillu.
