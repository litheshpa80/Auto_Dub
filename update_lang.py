"""Script to update dub_video_clone.py with multi-language support."""

content = open('f:/VC/dub_video_clone.py', 'r', encoding='utf-8-sig').read()

# 1. Update transcribe_and_translate signature and body
old1 = 'def transcribe_and_translate(chunks, model_name="large"):\n    model = whisper.load_model(model_name)\n    all_segments = []\n    for idx, (chunk_path, offset) in enumerate(chunks):\n        result = model.transcribe(\n            chunk_path,\n            language="kn",\n            task="translate",\n            verbose=False,\n            condition_on_previous_text=True,\n            word_timestamps=True,\n        )'
new1 = 'def transcribe_and_translate(chunks, model_name="large", source_language=None):\n    model = whisper.load_model(model_name)\n    all_segments = []\n    for idx, (chunk_path, offset) in enumerate(chunks):\n        transcribe_kwargs = {\n            "task": "translate",\n            "verbose": False,\n            "condition_on_previous_text": True,\n            "word_timestamps": True,\n        }\n        if source_language and source_language != "auto":\n            transcribe_kwargs["language"] = source_language\n        result = model.transcribe(chunk_path, **transcribe_kwargs)'
content = content.replace(old1, new1)

# 2. Update dub_video signature
old3 = 'def dub_video(input_video, output_video, whisper_model="large",\n              speaker_sample_start=10, speaker_sample_duration=15,'
new3 = 'def dub_video(input_video, output_video, whisper_model="large",\n              source_language="auto",\n              speaker_sample_start=10, speaker_sample_duration=15,'
content = content.replace(old3, new3)

# 3. Update transcribe call in dub_video
old4 = 'segments = transcribe_and_translate(chunks, whisper_model)'
new4 = 'segments = transcribe_and_translate(chunks, whisper_model, source_language)'
content = content.replace(old4, new4)

# 4. Update CLI - add source-language arg
old5 = '    parser.add_argument("--whisper-model", default="large",\n                        choices=["tiny", "base", "small", "medium", "large"])'
new5 = '    parser.add_argument("--whisper-model", default="large",\n                        choices=["tiny", "base", "small", "medium", "large"])\n    parser.add_argument("--source-language", default="auto",\n                        help="Source language code: auto, kn, hi, ta, te, ml, fr, es, de, ja, ko, zh, ar, ru, etc.")'
content = content.replace(old5, new5)

# 5. Pass source_language in CLI call
old6 = '    dub_video(\n        input_video=args.input_video,\n        output_video=args.output_video,\n        whisper_model=args.whisper_model,'
new6 = '    dub_video(\n        input_video=args.input_video,\n        output_video=args.output_video,\n        whisper_model=args.whisper_model,\n        source_language=args.source_language,'
content = content.replace(old6, new6)

# 6. Update docstring
old7 = 'Kannada to English Video Dubbing with Voice Cloning (Improved Sync)\n- Clones the original speaker voice using XTTS v2'
new7 = 'Any Language to English Video Dubbing with Voice Cloning (Improved Sync)\n- Supports 100+ source languages (auto-detect or specify)\n- Clones the original speaker voice using XTTS v2'
content = content.replace(old7, new7)

# Write back without BOM
open('f:/VC/dub_video_clone.py', 'w', encoding='utf-8').write(content)
print('OK - dub_video_clone.py updated')
