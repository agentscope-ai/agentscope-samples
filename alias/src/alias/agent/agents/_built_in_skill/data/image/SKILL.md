---
name: image-file
description: Guidelines for handling image files
type: image
---

# Images Handling Specifications

## Goals

- Safely identify image properties and metadata without memory exhaustion.
- Accurately extract text (OCR) and visual elements (Object Detection/Description).
- Perform necessary pre-processing (resize, normalize, crop) for downstream tasks.
- Handle multi-frame or high-resolution images efficiently.

## Inspection (Always First)

- Identify Properties: Use lightweight libraries (e.g., PIL/Pillow) to get `format`, `size` (width/height), and `mode` (RGB, RGBA, CMYK).
- Check File Size: If the image is exceptionally large (e.g., >20MB or >100MP), consider downsampling or tiling before full processing.
- Metadata/EXIF Extraction:
  - Read EXIF data for orientation, GPS tags, and timestamps.
  - Correction: Automatically apply EXIF orientation to ensure the image is "upright" before visual analysis.

## Content Extraction & Vision

- Vision Analysis:
  - Use multimodal vision models to describe scenes, identify objects, and detect activities.
  - For complex images (e.g., infographics, UI screenshots), guide the model to focus on specific regions.
- OCR (Optical Character Recognition):
  - If text is detected, specify whether to extract "raw text" or "structured data" (like forms/tables).
  - Handle low-contrast or noisy backgrounds by applying pre-filters (grayscale, binarization).
- Format Conversion: Convert non-standard formats (e.g., HEIC, TIFF) to standard formats (JPEG/PNG) if tools require it.

## Handling Large or Complex Images

- Tiling: For ultra-high-res images (e.g., satellite maps, medical scans), split into overlapping tiles to avoid missing small details.
- Batching: Process multiple images using generators to keep memory usage stable.
- Alpha Channel: Be mindful of transparency (PNG/WebP); decide whether to discard it or composite against a solid background (e.g., white).

## Best Practices

- Safety First: Validate that the file is a genuine image (not a renamed malicious script).
- Graceful Failure: Handle corrupted files, truncated downloads, or unsupported formats with descriptive error logs.
- Efficiency: Avoid unnecessary re-encoding (e.g., multiple JPEG saves) to prevent "generation loss" or artifacts.
- Process images individually or in small batches to prevent system crashes
- Consider memory usage when working with large or high-resolution images
- Resource Management: Close file pointers or use context managers (`with Image.open(...) as img:`) to prevent memory leaks.
