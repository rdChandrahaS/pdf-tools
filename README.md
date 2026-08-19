# pdf-tools

A local command-line PDF/image utility designed to work like `ffmpeg`: open a shell in the directory containing your files, run `pdf-tools`, choose an operation, and the results are written to `./output/`.

## Current workflow

```text
pdf-tools
  1. Image -> PDF
      1. Convert every image separately
      2. Convert images into one PDF
  2. Merge PDF
  0. Exit
```

### Image -> PDF

For separate conversion, only supported image files directly in the current directory are processed. Unsupported files such as TXT, MP4, DOCX, and PDF are ignored.

For a single PDF, the tool can:

- process images directly in the current directory and save them under a name you choose;
- process every image-containing folder directly inside the current directory, creating one PDF per folder using the folder name.

The scan is intentionally **not recursive** beyond those immediate folders.

### Output

All generated PDFs are placed in:

```text
./output/
```

The tool avoids overwriting an existing file by adding a numeric suffix such as `(1)`.

### Image quality

No resizing or intentional lossy recompression is performed. JPEG files are embedded using their existing JPEG bitstream. Other supported formats are decoded and stored with lossless Flate compression; transparent images are composited onto a white background.

### Large image sets

For a large single-PDF job, images are processed in chunks (100 images by default). Temporary chunk PDFs are used and removed automatically. This avoids creating one temporary PDF per image while keeping very large jobs manageable.

## Install

With `uv`:

```bash
uv tool install .
```

Or for a local editable installation:

```bash
uv pip install -e .
```

Then run from any working directory:

```bash
pdf-tools
```
