---
inclusion: always
---

# Text-First Paradigm and Asset Handling Protocol

This document establishes the mandatory protocol for extracting, managing, and inspecting image assets across Kiro workspaces.

| Protocol Phase | Primary Boundary | Concrete Standard |
| :--- | :--- | :--- |
| **Asset Ingestion** | Metadata extraction | Pair each image immediately with structured sidecar text |
| **Asset Triage** | Text-first filtering | Filter dimensions, formats, and themes strictly via text data |
| **Visual Inspection** | Targeted sampling | Cap binary image inspection to 1 to 3 targeted files |

---

## 1. Multimodal Bottleneck and Context Preservation

Direct binary image inspection consumes high context token volumes:
1. **Token Costs**: Reading raw image binaries creates heavy inference delays and consumes token budgets rapidly.
2. **Prohibition of Batch Vision**: Agents must never execute batch visual scans to inspect file dimensions, aspect ratios, or general image topics.
3. **Latency Bounds**: Triage image catalogs via structured text files to maintain fast interactive loops.

---

## 2. Mandatory Immediate Metadata Pairing

Every image saved or downloaded must link to a structured sidecar text file (`.meta.yaml` or `.meta.json`):
1. **Required Minimum Fields**:
   - `dimensions`: Width and height in pixels (`px`).
   - `aspect_ratio`: Numerical ratio and standard classification (landscape, portrait, square).
   - `format`: Concrete file format (`png`, `webp`, `jpeg`, `svg`).
   - `size_bytes`: Integer byte count.
   - `hash`: SHA-256 integrity digest string.
   - `semantic_description`: Rich text description of image content and focal subjects.
   - `context`: Application scope, capture origin, and source URI.
2. **Atomic Ingestion**: Never download an image without generating its companion sidecar metadata record during the same operation.

---

## 3. Surgical Visual Inspection

Binary image viewing must remain an exception rather than the default:
1. **Text Triage First**: Perform all initial sorting, filtering, resolution validation, and theme filtering through text metadata files.
2. **Minimal Sample Limit**: Restrict binary inspection calls (`view_file` on binary graphics) to 1 to 3 selected candidate assets.
3. **Indispensable Human Validation**: Reserve binary inspection strictly for final qualitative layout confirmation when automated text checks cannot decide aesthetic fit.
