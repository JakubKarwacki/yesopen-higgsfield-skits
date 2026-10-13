"""The production graph: project specification, approved audio, native API templates, explicit edit decisions."""
def configure(old):
    project = 'YESOPEN_PROJECT'
    def node(title, kind, inputs, outputs, widgets=(), size=(340, 160)):
        return (title, kind, [(name, typ, False) for name, typ in inputs], outputs, list(widgets), size)
    def step(title, kind):
        return node(title, kind, [('project', project)], [('project', project), ('log', 'STRING')])
    def gate(number, name):
        return node(f'Bramka {number} · {name}', 'YesOpenGate', [('project', project)], [('project', project)],
                    [f'{number} · ' + ('Scenariusz (Twoje TAK)' if number == 2 else 'Obsada (wybrane stille)' if number == 3 else name), False])
    old['STAGES'] = [
        ('proj', '__project__', 'Projekt i decyzje', 'Scenariusz, obsada i parametry pochodzą z projektu. Bramki wymagają świadomej zgody.', '#5c6370', 0, 0),
        ('cast', '__cast__', 'Kandydaci obsady', 'Opcjonalnie: jeden zestaw kandydatów na postać, seed wspólny dla generatora i zapisu. Istniejące stille są pomijane.', '#61afef', 1, 1),
        ('tts', 'audio-chatterbox_tts_multilingual', 'Głos z projektu', 'Tekst, język, próbka głosu, ekspresja i seed z lines.json. Odsłuch jest wymagany przed generacją wideo.', '#98c379', 0, 1),
        ('fit', '__fit__', 'Dopasowanie i odsłuch', 'Dopasowanie używa tylko aktualnego wykonania. fit konfiguruje lead, tail, min_ratio i max_pause; domyślnie zachowuje pauzy. Zatwierdzenie obejmuje tylko wskazane kwestie.', '#98c379', 0, 2),
        ('take', '__take__', 'Ujęcia MiniMax H3', 'Domyślny silnik: h3-talk, z zatwierdzonym audio. Pełne parametry z projektu, wspólne szablony API, audio dopełnione do siatki klatek. Upscale i interpolacja tylko gdy enabled w take.postprocess.', '#e5c07b', 0, 3),
        ('edit', '__edit__', 'Montaż i muzyka', 'Najpierw pełna selekcja ujęć i EDL. Muzyka: enabled=false, mode=existing lub generate. Generowanie wymaga specyfikacji; długość wynika z montażu. Napisy respektują captions.enabled.', '#56b6c2', 0, 4),
        ('formats', '__formats__', 'Render i QA wybranych formatów', 'Zakres pochodzi z project.formats. Każdy format renderowany z EDL i sprawdzany; wyłączenie napisów nie uruchamia ASR do ich dodania.', '#61afef', 0, 5),
        ('deliver', '__deliver__', 'Dostawa', 'Tylko formaty projektu po poprawnym QA. Manifest obejmuje pliki tej dostawy. Bez publikowania.', '#98c379', 0, 6),
    ]
    old['BUILT'] = {s[1] for s in old['STAGES'] if s[1].startswith('__')}
    old['MUTED'] = set()
    old['EXTRA_NODES'] = {}
    old['TITLE'] = 'YESOPEN SKIT PIPELINE · projekt → zatwierdzone głosy → MiniMax H3 → montaż → QA → dostawa. Tryb CPU służy do podglądu. Ustawienia generacji i decyzje o muzyce, napisach oraz formatach pochodzą z projektu.'
    old['PIPELINE_NODES'] = {
        'proj': [old['PIPELINE_NODES']['proj'][0], gate(1, 'Referencja'), gate(2, 'Scenariusz'), gate(3, 'Obsada'),
                 old['PIPELINE_NODES']['proj'][4], old['PIPELINE_NODES']['proj'][5]],
        'cast': [node('Kandydaci obsady', 'YesOpenCast', [('project', project)], [('report', 'STRING')], [0, False]),
                 node('Wariant sceny', 'YesOpenSceneVariant', [('project', project), ('line', 'STRING')], [('report', 'STRING')], ['l01', 'broll', False])],
        'fit': [old['PIPELINE_NODES']['fit'][0],
                node('Odsłuch zatwierdzony', 'YesOpenVoiceApproval', [('project', project), ('audio', 'AUDIO'), ('line', 'STRING')], [('audio', 'AUDIO')], ['l01', False]),
                old['PIPELINE_NODES']['fit'][2]],
        'take': [node('Generuj ujęcie', 'YesOpenGenerateTake', [('project', project), ('line', 'STRING'), ('audio', 'AUDIO')], [('video', 'VIDEO')], ['l01'], (340, 180)),
                 old['PIPELINE_NODES']['film'][0]],
        'edit': [node('Komplet ujęć', 'YesOpenJoinProduction', [('project', project)], [('project', project), ('report', 'STRING')]),
                 gate(4, 'Ujęcia'), step('Assety montażu', 'YesOpenBuildAssets'), step('Plan montażu', 'YesOpenMakeEDL'),
                 node('Decyzja o muzyce', 'YesOpenMusic', [('project', project)], [('project', project), ('path', 'STRING')]),
                 step('Końcowy EDL', 'YesOpenMakeEDL')],
        'formats': [gate(5, 'Montaż'), step('Render wybranych formatów', 'YesOpenRenderFormats'), step('QA wybranych formatów', 'YesOpenQAFormats')],
        'deliver': [gate(6, 'Formaty i QA'), step('Wersje do wysyłki', 'YesOpenEncodeVariants')],
    }
    links = []
    def wire(stage1, name1, slot, stage2, name2, input):
        links.append(((stage1, name1, slot), (stage2, name2, input)))
    for a,b in [('Projekt','Bramka 1 · Referencja'),('Bramka 1 · Referencja','Bramka 2 · Scenariusz'),
                ('Bramka 2 · Scenariusz','Bramka 3 · Obsada'),('Bramka 2 · Scenariusz','Kwestia z projektu'),('Projekt','Status projektu')]:
        wire('proj',a,0,'proj',b,'project')
    wire('proj','Bramka 2 · Scenariusz',0,'cast','Kandydaci obsady','project')
    wire('proj','Bramka 3 · Obsada',0,'cast','Wariant sceny','project')
    wire('proj','Kwestia z projektu',7,'cast','Wariant sceny','line')
    for slot,name in [(0,'text'),(1,'audio_prompt'),(2,'exaggeration'),(3,'cfg_weight'),(4,'seed'),(8,'language')]:
        wire('proj','Kwestia z projektu',slot,'tts','FL_ChatterboxMultilingualTTS',name)
    wire('proj','Bramka 3 · Obsada',0,'fit','Dopasuj kwestię','project')
    wire('tts','FL_ChatterboxMultilingualTTS',0,'fit','Dopasuj kwestię','audio')
    for slot,name in [(7,'line'),(4,'seed')]:
        wire('proj','Kwestia z projektu',slot,'fit','Dopasuj kwestię',name)
    wire('proj','Bramka 3 · Obsada',0,'fit','Odsłuch zatwierdzony','project')
    wire('proj','Kwestia z projektu',7,'fit','Odsłuch zatwierdzony','line')
    wire('fit','Dopasuj kwestię',0,'fit','Odsłuch zatwierdzony','audio')
    wire('fit','Dopasuj kwestię',0,'fit','Odsłuch kwestii','audio')
    for name in ['Generuj ujęcie','Ujęcie do projektu']:
        wire('proj','Bramka 3 · Obsada',0,'take',name,'project')
        wire('proj','Kwestia z projektu',7,'take',name,'line')
    wire('fit','Odsłuch zatwierdzony',0,'take','Generuj ujęcie','audio')
    wire('take','Generuj ujęcie',0,'take','Ujęcie do projektu','video')
    chain = [('take','Ujęcie do projektu'),('edit','Komplet ujęć'),('edit','Bramka 4 · Ujęcia'),('edit','Assety montażu'),
             ('edit','Plan montażu'),('edit','Decyzja o muzyce'),('edit','Końcowy EDL'),('formats','Bramka 5 · Montaż'),
             ('formats','Render wybranych formatów'),('formats','QA wybranych formatów'),('deliver','Bramka 6 · Formaty i QA'),('deliver','Wersje do wysyłki')]
    for (s,a),(t,b) in zip(chain,chain[1:]):
        wire(s,a,0,t,b,'project')
    old['LINKS'] = links
