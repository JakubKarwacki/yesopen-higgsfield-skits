# Końcowa analiza layoutu i rozmiarów — 12 października 2026

> Zapis historyczny implementacji lub wykonanej produkcji. Od 13 października 2026 głównym wyborem projektu jest MiniMax H3, a Wan 3.0 hostowany lokalnie jest alternatywą do testów. Nazwy poprzednich modeli i wyniki poniżej opisują stan z daty raportu; bieżące instrukcje i status migracji: references/video-models.md.

Analizowana wersja: `yesopen-skit-pipeline-layout-v7`. Pomiary wykonano na
rzeczywistych elementach DOM ComfyUI, po wejściu do każdego z siedmiu podgrafów.
Przegląd dotyczy geometrii, nie wykonania produkcji na GPU.

## Wynik pomiarów

| Zakres | Węzły | Nakładające się ramki | Rozbieżności rozmiaru ponad 2 px |
| --- | ---: | ---: | ---: |
| Główny graf | 81 | 0 | 0 |
| Z-Image | 9 | 0 | 0 |
| LTX-2.3 | 53 | 0 | 0 |
| MiniMax H3 | 21 | 0 | 0 |
| Qwen | 22 | 0 | 0 |
| Upscale | 18 | 0 | 0 |
| LTX-2.5 | 47 | 0 | 0 |
| Interpolacja | 8 | 0 | 2 |

Razem: 259 węzłów. Ramki obejmują nagłówki. Węzły wejść/wyjść podgrafów,
rysowane na canvasie poza `.lg-node`, nie są objęte tabelą DOM. ComfyUI zmieniło
część identyfikatorów węzłów wewnętrznych; porównano je według pozycji, gdy
pierwotny identyfikator nie występował w DOM.

## Pozostałe możliwości optymalizacji

1. **Pola promptów mają największy zapas wysokości.** Z-Image: `CLIPTextEncode`
   nr 27 ma 650 px wysokości body; LTX-2.5: nr 364 ma 740 px. Na sprawdzonym
   podglądzie Z-Image znaczna część pola była pusta. Proponowana następna próba:
   300–360 px dla Z-Image i 340–420 px dla LTX-2.5, ze scrollowaniem dłuższego
   tekstu. Są to wartości do przymiarki, nie potwierdzone minima. Zmiana wymaga
   ponownego pomiaru portów widgetów i przeliczenia tras.

2. **Dwa węzły interpolacji wymagają aktualizacji geometrii.** `PrimitiveBoolean`
   nr 13 zapisano jako 310 × 90 px; frontend rysuje 325 × 90 px.
   `GetVideoComponents` nr 3 zapisano jako 230 × 100 px; frontend rysuje
   230 × 114 px. Nie powodują teraz nakładania ramek, ale generator powinien
   uwzględnić ich rzeczywiste wymiary przed kolejnym zagęszczeniem.

3. **Sztywne rozmiary podglądów można uzależnić od roli.** Puste `PreviewAny`
   wewnątrz LTX mają wysokość 360 px. Węzły podglądu pojedynczego promptu można
   przymierzyć do 180–220 px, pozostawiając większy obszar dla raportów QA.
   Podglądów obrazu/wideo nie należy zmniejszać według tej samej reguły:
   potrzebują miejsca na materiał 9:16 i kontrolki.

4. **Dalsze ściskanie wszystkich odstępów ma mniejszy sens niż zmniejszenie
   wybranych pól.** Główny graf ma 15720 × 3581 px; brak kolizji potwierdzono
   także po ostatnich zmianach. Duża szerokość wynika m.in. z dziewięciu kolejnych
   kolumn zależności. Odstępy korytarzy rosną wraz z liczbą pasów. Ich globalne
   zmniejszenie może pogorszyć czytelność tras.

5. **Kryterium ustawienia sekcji nadal jest przybliżeniem.** Annealer minimalizuje
   oszacowaną długość i liczbę załamań, nie końcową geometrię wyrenderowanych tras.
   Cztery dodatkowe ziarna losowe nie zmniejszyły 34 widocznych punktów głównego
   grafu. To nie dowodzi globalnej optymalności. Kolejny większy krok to ocenianie
   kandydatów po rzeczywistym trasowaniu, z karą za punkty i zajętą powierzchnię.

## Zalecenie

Zachować obecny układ głównego grafu. Najpierw skorygować dwa węzły interpolacji,
następnie przymierzyć niższe pola promptów i podglądów tekstowych wewnątrz
podgrafów. Po każdej zmianie rozmiaru ponownie zmierzyć porty, przeliczyć trasy
i sprawdzić ramki oraz czytelność w ComfyUI. W tej analizie nie zmieniono
rozmiarów ani logiki workflow; przywrócono widok głównego grafu.
