# PixelForge (Streamlit)

Neon-themed photo editor, video editor, Music Studio and Gemini AI image generator.

## Features
- **Photo Editor**: 500 filters, 500 effects, 500 templates, adjust, crop, rotate/flip, text layers, undo/redo, Gemini AI edits + captions
- **Video Editor**: trim, speed 0.25x-4x, looks, filmstrip timeline, original-sound mix, add song, Gemini AI, one-pass FFmpeg export
- **Music Studio**: photos -> beat-synced slideshow, or add a song to a video
- **AI Generate**: text -> image, then edit it in the Photo Editor

## Run
    pip install -r requirements.txt       # FFmpeg must be installed (packages.txt on Streamlit Cloud)
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml    # add your keys
    streamlit run app.py

Keys: Gemini (aistudio.google.com), Jamendo client id (devportal.jamendo.com). Both stay server-side.

## Layout
    app.py          splash + hub + sidebar navigation
    views/          pages (common = theme + shared widgets)
    pixelforge/     core: catalog, edit state, rendering, FFmpeg export, Gemini, beat detection

## Notes
- Many Jamendo tracks are CC "-NC" (non-commercial); the UI warns about this.
- Spotify / YouTube Music connect exists only in the Flutter app.
- Effects other than Vignette, Film Grain and Duotone are photo / preview only in video export.
