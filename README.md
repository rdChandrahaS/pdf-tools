# pdf-tools

A local, offline command-line PDF and image toolkit designed to work like `ffmpeg`: open a shell in the directory containing your files, run `pdf-tools`, choose an operation, and the generated results are written to `./output/`.

## Features

### Image -> PDF

- Convert every supported image into a separate PDF.
- Convert all images in the current directory into one PDF.
- Select specific images for one PDF.
- Convert selected immediate subfolders into one PDF per folder.
- Natural filename ordering (`page2` before `page10`).
- Supports JPG/JPEG, PNG, WEBP, BMP, TIFF and GIF.
- JPEG files are embedded from their existing JPEG bitstream; other formats use lossless Flate compression.
- Transparent images are composited onto a white background.
- Large image batches are processed through temporary chunks to keep memory usage manageable.

### Merge PDF

- Select the PDFs to merge from the current directory.
- Files are merged in natural filename order.
- Large merges use temporary internal batches.
- Existing output files are never overwritten.

### PDF Tools

- Inspect page count, file size, encryption status and metadata.
- Split a PDF into one PDF per page.
- Rotate every page by 90°, 180° or 270° clockwise.

### Compress PDF

The compressor previews the result **before saving it**. It creates a temporary compressed PDF, measures its actual size, and shows:

- Original file size.
- Estimated/resulting compressed size.
- Estimated bytes saved and percentage reduction.
- Page count and detected image count.

You then choose whether to keep that result.

#### Lossless compression

- Does not intentionally recompress or downsample embedded images.
- Removes unused PDF objects.
- Compresses uncompressed streams and fonts where possible.
- Uses PDF object streams where supported.
- No visual quality loss is intended.

Lossless compression may produce only a small reduction, or occasionally make a PDF slightly larger depending on how the source PDF was created. The preview lets you see the actual result first.

#### Lossy compression

- Keeps text and vector page content as PDF content.
- Recompresses/downsamples raster images instead of converting whole pages into images.
- Choose a target DPI from presets or enter a custom DPI.
- Choose JPEG quality from presets or enter a custom quality value from 1–100.
- Optionally convert color images to grayscale for additional reduction.

Typical trade-off:

- Higher DPI + higher quality → larger file, better image quality.
- Lower DPI + lower quality → smaller file, more visible image degradation.

Because the tool previews the generated PDF, you can try a lossless pass first and only move to lossy settings when the measured reduction is not enough.

## Output

Generated PDFs are written to:

```text
./output/
```

The tool avoids overwriting an existing file by adding suffixes such as `(1)`.

Temporary compression previews and large-job working files are removed automatically.

## Install

With `uv`:

```bash
uv tool install .
```

For an existing installation, force-update the command after replacing the project files:

```bash
uv tool install --force .
```

Or for a local editable installation:

```bash
uv pip install -e .
```

Then run from any working directory:

```bash
pdf-tools
```

## Python

Python 3.13+ is required.
