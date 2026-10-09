# PDF-TOOL

A desktop application for working with PDF files, built to run locally on your computer so your documents never leave your machine.

> **Note:** Items marked with `[EDIT]` are placeholders. Replace them with details that match your project.

---

## What is it?

PDF-TOOL is a simple desktop app that lets you manage PDF files without needing online services or paid software.

### Features `[EDIT: keep only what your app actually does]`

- Merge multiple PDFs into one
- Split a PDF into separate pages or ranges
- Compress PDFs to reduce file size
- Convert PDFs to/from other formats (images, Word, etc.)
- Rotate, reorder, or delete pages
- Works offline, with no uploads

---

## Requirements `[EDIT]`

- Windows 10 or 11
- [Python 3.9+](https://www.python.org/downloads/) (check "Add Python to PATH" during install)
- Git (optional, only needed if you clone the repo)

---

## How to download

### Option 1: Download as ZIP (easiest)

1. Go to https://github.com/Prajwal-454/PDF-TOOL
2. Click the green **Code** button
3. Click **Download ZIP**
4. Right-click the downloaded file and choose **Extract All**

### Option 2: Clone with Git

```bash
git clone https://github.com/Prajwal-454/PDF-TOOL.git
cd PDF-TOOL
```

---

## Installation `[EDIT]`

Open Command Prompt or PowerShell inside the project folder, then install the dependencies:

```bash
pip install -r requirements.txt
```

---

## How to use

1. Start the app:

   ```bash
   python main.py
   ```

   `[EDIT: replace main.py with your actual entry file]`

2. In the app window, click **Open / Add Files** and select your PDF(s).
3. Choose the action you want (merge, split, compress, etc.).
4. Click **Run** / **Save** and pick where to save the result.
5. Your processed file will appear in the folder you selected.

---

## Project structure `[EDIT]`

```
PDF-TOOL/
├── main.py            # App entry point
├── requirements.txt   # Dependencies
└── README.md          # You are here
```

---

## Troubleshooting

- **`python` is not recognized:** Reinstall Python and tick "Add Python to PATH", or use `py` instead of `python`.
- **`pip` install fails:** Try `python -m pip install -r requirements.txt`.
- **App won't open a PDF:** Make sure the file isn't password-protected or corrupted.

---

## Contributing

Issues and pull requests are welcome. Fork the repo, make your changes on a new branch, and open a pull request.

## License `[EDIT]`

Add a license (for example MIT) by creating a `LICENSE` file, then mention it here.

---

Made by [Prajwal](https://github.com/Prajwal-454)
