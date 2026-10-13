# TODO

Robocza lista dalszego rozwoju pipeline’u. Kolejność pokazuje zależności i proponowany przebieg prac; zakres może się zmienić po testach MVP.

## Research i przygotowanie treści

- [ ] Porównać dostępne API do przeglądania mediów społecznościowych z przeglądaniem ich przez agenta w przeglądarce. Jeśli przeglądarka okaże się lepsza, przygotować konta społecznościowe dla pipeline’u.
- [ ] Przenieść odpowiedzialność za kompozycję scenariusza z Qwen uruchamianego na instancji do Gemini w bezpłatnym planie.
- [ ] Zbudować bazę dostępnych głosów, pogrupowaną według języka i opisaną pod kątem ich charakterystyki. Agent scenarzysta ma wybierać głos z bazy, zamiast wymyślać niedostępny głos.
- [ ] Podłączyć Gemini TTS i udostępnić je agentowi jako źródło głosów z przygotowanej bazy.
- [ ] Opracować konwerter scenariusza na prompty generacyjne dla poszczególnych ujęć.
- [ ] Przebudować przygotowywanie kontekstu dla generatora: pobierać screeny z materiału dostępnego online zamiast pobierać całe nagranie, rozdzielać je na klatki i przetwarzać każdą klatkę osobno.
- [ ] Sprawdzić edycję screenów referencyjnych przez Nano Banana i włączyć wybrane rozwiązanie do pipeline’u.

## Montaż i publikacja

- [ ] Przebudować moduł napisów w finalnym nagraniu i dodać bramkę decyzyjną, która pozwala wybrać, czy napisy mają być dodane.
- [ ] Dodać analogiczną bramkę decyzyjną dla muzyki w finalnym nagraniu.
- [ ] Opracować komponent przygotowujący finalny post do mediów społecznościowych: poprawny opis, słowa kluczowe oraz link do użytej muzyki, jeśli została dodana.

## Sprawdzenie i usprawnienia

- [ ] Przeprowadzić testy MVP całego pipeline’u.
- [ ] Optymalizować koszty użycia modeli Gemini.
- [ ] Opracować asynchroniczne wykonywanie pipeline’u.

## Dalsze pomysły

- To be continued…
