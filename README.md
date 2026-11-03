# qr-code-identifiers

Small suite of Python scripts to generate identification QR codes and exam kit PDFs.

## Usage from the terminal

Open PowerShell or another terminal in the project folder, then run the generator with Python:

```powershell
python qr-generator-era-exams-test.py
```

By default, the script reads `era_nna_exams_2026_consolidado.csv`, generates 10 kits, and creates `kits_desde_csv.pdf`.

### Generate kits from a CSV

```powershell
python qr-generator-era-exams-test.py --csv --cantidad 20 --output-prefix kits_20
```

To use a different CSV file:

```powershell
python qr-generator-era-exams-test.py --csv-path "data\estudiantes.csv" --cantidad 15 --output-prefix estudiantes
```

### Generate blank cards

```powershell
python qr-generator-era-exams-test.py --sin-csv --cantidad 10 --id-inicial 200000 --output-prefix kits_vacios
```

### Choose the page orientation

Portrait uses a dynamically calculated 2-column grid. Landscape adds a column and uses a 3-column by 4-row grid for A4 by sizing the cards to the available page area. A4 and Letter dimensions are both supported.

```powershell
python qr-generator-era-exams-test.py --sin-csv --cantidad 20 --orientacion landscape --tamano-pagina A4 --output-prefix kits_horizontales
```

### Distribute cards across multiple PDF files

Use `--cantidad-archivos` to divide the total number of cards evenly among several PDF files. For example, 10 cards divided into 3 files produce groups of 4, 3 and 3 cards.

```powershell
python qr-generator-era-exams-test.py --sin-csv --cantidad 10 --cantidad-archivos 3 --output-prefix kits_separados
```

The files are named `kits_separados_1_de_3.pdf`, `kits_separados_2_de_3.pdf`, and `kits_separados_3_de_3.pdf`.

### Available options

| Option | Description | Default |
|---|---|---|
| `--csv` | Read student data from a CSV | CSV mode |
| `--sin-csv` | Generate blank cards | Off |
| `--csv-path` | Path to the CSV file | `era_nna_exams_2026_consolidado.csv` |
| `--cantidad` | Number of cards or kits | `10` |
| `--id-inicial` | First generated ID for blank cards | `100000` |
| `--output-prefix` | PDF output filename without `.pdf` | `kits_desde_csv` |
| `--orientacion`, `--orientation` | Page orientation: `portrait` or `landscape` | `portrait` |
| `--tamano-pagina`, `--page-size` | Page format: `A4` or `letter` | `A4` |
| `--cantidad-archivos`, `--file-count` | Number of PDF files that receive the total cards | `1` |

Show the built-in help at any time:

```powershell
python qr-generator-era-exams-test.py --help
```

## Requirements

Install the Python dependencies:

```powershell
python -m pip install qrcode reportlab pandas pillow
```

The PDF uses the bundled files in the `fonts/` directory, so it does not require an installed system font. Keep that directory next to `qr-generator-era-exams-test.py`.
