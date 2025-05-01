# RipzBuddy - GUI Edition

A next-generation toolkit for automating NFO, playlist, and checksum creation for your FLAC music collections.

## Features
- Smart NFO tracklist: VA/single-artist, multi-disc, proper numbering
- Capitalized FLAC filenames
- CUE, M3U, SFV, and log file support
- Discogs metadata integration
- Batch folder processing
- Robust error handling & logs
- Customizable ASCII art/release group template

---

## Step-by-step Quick Start

1. **Create a start.bat file** with the following content (in your app folder):
   ```bat
   @echo off
   python nfo_gui.py
   ```
2. **Run the start.bat file** to launch the app.

3. **Fill in all relevant info:**
   - ASCII art for your release group
   - Ripper name
   - Release group name
   - Group name
   - Choose Vinyl or CD

4. **Go to your Discogs page**, create a general use token, and copy it into the 'Discogs Token' field in the app.

5. **If happy with your settings, save your template** anywhere on your system.

6. **To process a batch of releases:**
   - Click 'Start Batch Processing'
   - Select your root folder containing all release folders
   - Click Open

7. **The batch process will start, with a log showing all tasks being performed.**

That's it—enjoy your newly created releases!

---

### Tips
- For multi-disc releases, keep all discs in the same folder (tracks 101, 201, etc.).
- Create an `id.tsh` file with the Discogs release URL for best metadata.
- Backup your results!
- Need help? See About or contact support.

---

## Next Update
Even smarter auto id.tsh creation and more!

---

## Author
Developed by Cobus Galvin (Galvitech)

Support: cobusgalvin@gmail.com  
GitHub: [ElectronicPunkZA](https://github.com/ElectronicPunkZA)

Powered by Python, Tkinter, and open music APIs.

## License
MIT License. See [LICENSE](LICENSE) for details.
