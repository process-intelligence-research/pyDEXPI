import pandas as pd
import pytest

from pydexpi.dexpi_classes import equipment, physicalQuantities
from pydexpi.dexpi_classes.dexpiModel import ConceptualModel, DexpiModel
from pydexpi.exports import table_export


@pytest.fixture
def dummy_equipment():
    """Create a pump instance to test equipment listing."""
    return equipment.Pump(
        tagName="EQ-001",
        designPressureHead=physicalQuantities.Length(
            value=60.0, unit=physicalQuantities.LengthUnit.Metre
        ),
    )


def test_format_string():
    """Test string formatting from DEXPI naming to column header."""
    assert table_export.format_string("TagName") == "Tag name"
    assert table_export.format_string("EquipmentType") == "Equipment type"


def test_float_to_str():
    """Test float to string conversion."""
    assert table_export.float_to_str(60.0) == "60"
    assert table_export.float_to_str(60.5) == "60.5"
    assert table_export.float_to_str(0.0) == "0"


def test_reorder_columns():
    """Test reordering of DataFrame columns."""
    df = pd.DataFrame([{"B": 1, "A": 2, "C": 3}])
    priority = ["A", "C"]
    result = table_export.reorder_columns(df, priority)
    assert result.columns.tolist() == ["A", "C", "B"]


def test_make_equipment_list(dummy_equipment):
    """Test making equipment list DataFrame from DEXPI model."""
    conceptual_model = ConceptualModel(taggedPlantItems=[dummy_equipment])
    model = DexpiModel(conceptualModel=conceptual_model)
    df = table_export.make_equipment_list(model)
    assert "Tag" in df.columns
    assert "Equipment type" in df.columns
    assert "Design pressure head" in df.columns
    assert df.iloc[0]["Tag"] == "EQ-001"
    assert df.iloc[0]["Equipment type"] == "Pump"
    assert df.iloc[0]["Design pressure head"] == "60 m"


def test_export_tables(monkeypatch, tmp_path):
    """Test export_tables function for file creation."""

    # Minimal test to check file creation
    def mock_make_equipment_list(model):
        return pd.DataFrame([{"Tag": "EQ-001", "Equipment type": "Pump", "Length": "60 m"}])

    monkeypatch.setattr(table_export, "make_equipment_list", mock_make_equipment_list)
    model = DexpiModel()
    out_path = tmp_path / "test_export"
    table_export.export_tables(model, str(out_path), lists=["equipment"], formats=[".csv"])
    csv_file = tmp_path / "test_export_equipment.csv"
    assert csv_file.exists()
    df = pd.read_csv(csv_file)
    assert "Tag" in df.columns
    assert "Equipment type" in df.columns
    assert "Length" in df.columns


def test_no_list_or_format_specification(monkeypatch, tmp_path):
    """Test export_tables function without list or format specification."""

    # Minimal test to check file creation
    def mock_make_equipment_list(model):
        return pd.DataFrame([{"Tag": "EQ-001", "Equipment type": "Pump", "Length": "60 m"}])

    monkeypatch.setattr(table_export, "make_equipment_list", mock_make_equipment_list)
    model = DexpiModel()
    out_path = tmp_path / "test_export"
    table_export.export_tables(model, str(out_path))
    xlsx_file = tmp_path / "test_export.xlsx"
    assert xlsx_file.exists()
    # Read the "Equipment" sheet from the Excel file
    df = pd.read_excel(xlsx_file, sheet_name="Equipment")
    assert "Tag" in df.columns
    assert "Equipment type" in df.columns
    assert "Length" in df.columns
