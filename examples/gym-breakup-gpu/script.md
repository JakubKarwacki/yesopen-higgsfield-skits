# It's not you. It's your invoices. (serwer GPU)

- **Status:** scenariusz zaakceptowany 2026-10-01 dla wersji z Higgsfield (`../gym-breakup/script.md`). Tę wersję zrobiliśmy 2026-10-02 na własnym serwerze GPU, żeby porównać oba silniki na tym samym scenariuszu i montażu.
- **Pomysł:** właściciel siłowni zrywa ze swoją agencją marketingową. Agencja straszy pytaniami „a kto będzie…?”, a on za każdym razem udaje, że nie wie. Wtedy jego telefon dzwoni powiadomieniem, które odpowiada na to pytanie. Agencja zaczyna podejrzewać, że ma kogoś innego. Funkcje YesOpen pojawiają się tylko jako puenty, a nie jako prezentacja.
- **Długość:** 61,4 s, pionowo 9:16, po angielsku.

## Wzór

„How to breakup with your girlfriend #shorts” z kanału Content Machine. Link: https://www.youtube.com/watch?v=NvKrK5S0yS4. Analiza własnymi słowami jest w `../gym-breakup/reference/analysis.md`. Klatki i transkrypcja wzoru zostały na komputerze, poza repozytorium, i nie trafiły na serwer.

## Postacie

- **Właściciel (OWNER):** to samo zdjęcie co w wersji z Higgsfield. Głos sklonowany z 8,6 s jego ujęcia z Seedance (`voices/owner.wav`).
- **Agencja (AGENCY):** to samo zdjęcie co w wersji z Higgsfield. Głos sklonowany z 7 s jej ujęcia (`voices/agency.wav`).

Oba głosy są wygenerowane, więc nie klonujemy głosu żadnej realnej osoby.

## Scenariusz

Kwestie są takie same jak w wersji z Higgsfield. Opisy gry pochodzą z `lines.json`: tak opisaliśmy każde ujęcie dla modelu wideo.

| # | Kto | Kwestia | Gra i ujęcie |
| --- | --- | --- | --- |
| 1 | OWNER | Hey… I think we should break up. | poważnie, trochę nerwowo, bierze oddech |
| 2 | AGENCY | You're breaking up… with your marketing agency? | szok, nachyla się do kamery |
| 3 | OWNER | It's not you. It's your invoices. | spokojnie, ze współczuciem |
| 4 | AGENCY | …Wow. | jedno słowo, potem urażona cisza, 1,6 s ogona |
| 5 | AGENCY | Fine. But who's going to answer all your questions? | odzyskuje pewność |
| 6 | OWNER | I don't know… | udaje zmartwienie; telefon się świeci, odwraca go ekranem do piersi. **DING**, baner |
| 7 | AGENCY | Who's going to reply to your reviews? | |
| 8 | OWNER | No idea. | po kwestii kaszle i odwraca wzrok. **DING**, baner |
| 9 | AGENCY | Who's going to post on your Instagram? | |
| 10 | OWNER | Not a clue. | po kwestii gwiżdże w bok. **DING**, baner |
| 11 | AGENCY | Who's going to get you to the top of Google Maps? | |
| 12 | OWNER | Honestly? Absolutely no idea. | wariant zdjęcia z shakerem przy brodzie; pije i nie ukrywa uśmiechu. **DING DING**, baner |
| 13 | AGENCY | Wait… are you seeing someone else? | mruży oczy, nachyla się |
| 14 | OWNER | What? …What? No. | udaje urażonego |
| 15 | AGENCY | Then who keeps texting you? | |
| 16 | OWNER | It's… just an app. | zawstydzony, unosi telefon tyłem do kamery |
| 17 | AGENCY | You're leaving us… for an app?! | krzyk |
| 18 | OWNER | It replies at two a.m. You reply in five business days. | wzrusza ramionami |
| 19 | AGENCY | Fine. You'll come crawling back. Don't even think about calling me. | wskazuje palcem, nachyla się, odwraca się i wychodzi z kadru |
| 20 | OWNER | What? Babe, no! Come back! | udawana rozpacz, sięga za nią ręką |
| 21 | OWNER | Hey, you. | 3,3 s ciszy: głowa w tył, ręce szeroko; telefon brzęczy, patrzy na niego i mówi czule |
| 22 | plansza | YesOpen · It's not you. It's your invoices. · yesopens.com | 2,6 s |

Banery powiadomień nakładamy w montażu, więc tekst jest dokładny. Model wideo nie pisze tekstu na ekranie.

## Co jest prawdą o produkcie

Puenty są te same co w wersji z Higgsfield. Źródła w treściach YesOpen (`business-card/messages/en/marketing.json`, `app.json`, `nav.json`):

| Puenta | Źródło |
| --- | --- |
| Odpowiedzi na pytania | agent: „I can reply to reviews, prepare a post and help improve your profile” |
| Odpowiedzi na opinie | „AI replies to every review, in your voice” |
| Instagram i Facebook | publikacja kampanii przez Meta |
| Pozycja w Mapach | „Be the #1 business on Google Maps”, „Daily Google Maps ranking tracking” |
| „Replies at 2 a.m.” | „AI runs your Google profile 24/7”, „even while you're closed” |

## Produkcja

- **Serwer:** 1× H200 w Verda, ComfyUI 0.35 z oficjalnymi szablonami (`gpu/` w skillu). Pierwsza instalacja trwała 10 min 40 s.
- **Zdjęcia:** z wersji z Higgsfield. Wariant z shakerem do kwestii 12 zrobił `still-edit` w 4 krokach.
- **Głos:** Chatterbox Multilingual, dwie próby każdej kwestii, potem `fit_lines.py`. Whisper sprawdza słowa, skrypt ucina wszystko po ostatnim słowie i daje 0,3 s ciszy na początku. Kwestie 12 i 18 nagraliśmy jeszcze cztery razy.
- **Ujęcia z ruchem ust:** LTX-2.3 do gotowej kwestii, jedno ujęcie na kwestię, 704×1280, 24 kl./s. W opisie każdego ujęcia jest zdanie, że kadr się nie zmienia, bo LTX lubi pod koniec najechać na twarz.
- **Montaż:** ten sam `cuts.json` co w wersji z Higgsfield, przepisany na ujęcia `l01`–`l21`, z tymi samymi przybliżeniami, banerami i planszą.

## Po produkcji

- **Gotowe:** 2026-10-02. Master 9:16, 1080×1920, 61,4 s (58,8 s scenki i 2,6 s planszy), −14,9 LUFS, true peak −1,3 dBTP, klatki co do jednej, Whisper słyszy dokładnie tekst napisów.
- **Zmiany względem scenariusza:**
  - kwestia 16: w pierwszym ujęciu pokazywał ekran telefonu, jak w scenariuszu; w powtórce (seed 616) trzyma telefon tyłem do kamery, więc nie widać wymyślonego ekranu;
  - kwestia 18: pierwsze próby mówiły „two AMA”, więc nagraliśmy ją jeszcze cztery razy, także z innym zapisem godziny; wygrał zapis „two a.m.”;
  - kwestia 21: „Hey, you.” pada po 3,3 s niemej radości, zrobionej w tym samym ujęciu (`silence_before` i własny opis ujęcia);
  - scenka jest o 12 s krótsza niż wersja z Higgsfield, bo każda kwestia jest przycięta do słów, zanim powstaje jej ujęcie.
- **Koszt:** 10,4 min pracy karty. Cała sesja z instalacją i testem wszystkich szablonów trwała ok. 1 h i kosztowała 4,86 USD.
- **Pliki:** `final/web/its-not-you-its-your-invoices-gpu-9x16.mp4` i plakat. Master odtwarzasz poleceniami z `README.md`.
