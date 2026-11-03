import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).with_name("qr-generator-era-exams-test.py")
SPEC = importlib.util.spec_from_file_location("qr_generator", SCRIPT_PATH)
qr_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qr_generator)


class LoadStudentsFromCsvTests(unittest.TestCase):
    def test_missing_csv_returns_empty_list(self):
        result = qr_generator.load_students_from_csv("archivo_inexistente.csv", limit=10)
        self.assertEqual(result, [])

    def test_normalizes_columns_deduplicates_ids_and_limits_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "students.csv"
            pd.DataFrame([
                {
                    "ID_NNA": "1",
                    "Nombre_Apellido": " Ana Pérez ",
                    "Sexo": "femenino",
                    "Distrito": " Centro ",
                    "Escuela_Nro": "12",
                    "Grado": "3",
                    "Turno": "mañana",
                    "Nivel": "Nivel 1",
                    "Facilitador": "Ana López",
                },
                {
                    "ID_NNA": "1",
                    "Nombre_Apellido": "Registro duplicado",
                    "Sexo": "m",
                    "Distrito": "Sur",
                    "Escuela_Nro": "15",
                    "Grado": "4",
                    "Turno": "tarde",
                },
                {
                    "ID_NNA": "002",
                    "Nombre_Apellido": "Luis Gómez",
                    "Sexo": "M",
                    "Distrito": "Norte",
                    "Escuela_Nro": "8",
                    "Grado": "2",
                    "Turno": "mañana",
                },
            ]).to_csv(csv_path, index=False, encoding="utf-8-sig")

            students = qr_generator.load_students_from_csv(str(csv_path), limit=1)

            self.assertEqual(len(students), 1)
            self.assertEqual(students[0]["id"], "1")
            self.assertEqual(students[0]["nombre"], "Ana Pérez")
            self.assertEqual(students[0]["sexo"], "F")
            self.assertEqual(students[0]["distrito"], "Centro")
            self.assertEqual(students[0]["nivel"], "Nivel 1")
            self.assertEqual(students[0]["facilitador"], "Ana López")


class GenerateExamKitsTests(unittest.TestCase):
    def test_divide_elements_distributes_remainder_across_first_files(self):
        groups = qr_generator.dividir_elementos(list(range(10)), 3)
        self.assertEqual([len(group) for group in groups], [4, 3, 3])
        self.assertEqual(sum(groups, []), list(range(10)))

    def test_page_layout_uses_different_grids_by_orientation(self):
        portrait_size, portrait_cols, portrait_rows, _, _ = qr_generator.get_page_layout("portrait")
        landscape_size, landscape_cols, landscape_rows, _, _ = qr_generator.get_page_layout("landscape")

        self.assertEqual((portrait_cols, portrait_rows), (2, 5))
        self.assertEqual((landscape_cols, landscape_rows), (3, 4))
        self.assertGreater(portrait_size[1], portrait_size[0])
        self.assertGreater(landscape_size[0], landscape_size[1])

    def test_supported_page_sizes_preserve_card_dimensions(self):
        reference_width = reference_height = None
        for page_size in ("A0", "A1", "A2", "A3", "A4", "A5", "A6", "letter"):
            page, cols, rows, card_width, card_height = qr_generator.get_page_layout("portrait", page_size)
            self.assertGreater(page[0], 0)
            self.assertGreater(page[1], 0)
            self.assertGreaterEqual(cols, 1)
            self.assertGreaterEqual(rows, 1)
            if reference_width is None:
                reference_width, reference_height = card_width, card_height
            self.assertEqual(card_width, reference_width)
            self.assertEqual(card_height, reference_height)

    def test_blank_card_generation_creates_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.join(temp_dir, "blank_kits")

            qr_generator.generate_exam_kits(
                usar_csv=False,
                cantidad=1,
                id_inicial=200000,
                output_prefix=output_prefix,
            )

            pdf_path = Path(output_prefix + ".pdf")
            self.assertTrue(pdf_path.is_file())
            self.assertGreater(pdf_path.stat().st_size, 0)

    def test_blank_cards_are_distributed_across_multiple_pdfs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.join(temp_dir, "distributed_kits")

            qr_generator.generate_exam_kits(
                usar_csv=False,
                cantidad=10,
                id_inicial=400000,
                output_prefix=output_prefix,
                cantidad_archivos=3,
            )

            expected_names = [
                "distributed_kits_1_de_3.pdf",
                "distributed_kits_2_de_3.pdf",
                "distributed_kits_3_de_3.pdf",
            ]
            for name in expected_names:
                pdf_path = Path(temp_dir) / name
                self.assertTrue(pdf_path.is_file())
                self.assertGreater(pdf_path.stat().st_size, 0)

    def test_landscape_blank_card_generation_creates_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.join(temp_dir, "landscape_kits")

            qr_generator.generate_exam_kits(
                usar_csv=False,
                cantidad=9,
                id_inicial=300000,
                output_prefix=output_prefix,
                orientacion="landscape",
            )

            pdf_path = Path(output_prefix + ".pdf")
            self.assertTrue(pdf_path.is_file())
            self.assertGreater(pdf_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
