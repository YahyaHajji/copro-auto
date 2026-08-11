from docx import Document

from copro_auto.documents.service import DocumentGenerationService
from copro_auto.documents.docx_renderer import resource_root


def all_text(path):
    document = Document(path)
    return "\n".join(
        [paragraph.text for paragraph in document.paragraphs]
        + [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    )


def test_generates_six_documents_with_critical_values(tmp_path, yasmin_project):
    files = DocumentGenerationService().generate(yasmin_project, tmp_path)
    assert len(files) == 6
    for path in files:
        text = all_text(path)
        assert "119753/59" in text
        if path.name != "Tableau_Recapitulatif.docx":
            assert "yasmin 71" in text.casefold()
    regulation = all_text(tmp_path / "Reglement_Copropriete.docx")
    for value in ("3522", "3239", "10000"):
        assert value in regulation
    assert yasmin_project.generations[-1].validation_ok


def test_yasmin_document_structures_and_legal_text_are_preserved(tmp_path, yasmin_project):
    DocumentGenerationService().generate(yasmin_project, tmp_path)
    table_b = Document(tmp_path / "Tableau_B.docx")
    regulation = Document(tmp_path / "Reglement_Copropriete.docx")
    recap = Document(tmp_path / "Tableau_Recapitulatif.docx")
    pv2 = Document(tmp_path / "PV_Division_2.docx")

    assert len(table_b.tables[0].rows) == 25
    assert len(regulation.tables[9].rows) == 27
    assert len(regulation.tables[12].rows) == 5
    assert [len(regulation.tables[index].rows) for index in range(2, 9)] == [2, 2, 1, 4, 2, 1, 3]
    assert [len(table.rows) for table in recap.tables] == [1, 6, 1, 4]
    assert [len(table.rows) for table in pv2.tables] == [2, 2, 1, 4, 3, 1, 3]
    assert pv2.tables[3].rows[3].cells[0].text.strip() == yasmin_project.levels[2].name

    table_a = Document(tmp_path / "Tableau_A.docx")
    table_a_xml_text = "".join(table_a.element.body.xpath(".//w:t/text()"))
    assert "Yasmine 27" not in table_a_xml_text
    assert "81819/38" not in table_a_xml_text
    assert yasmin_project.identity.property_name in table_a_xml_text
    assert yasmin_project.identity.land_title in table_a_xml_text

    header_cell = pv2.sections[0].header.tables[0].rows[0].cells[2]
    project_run = next(run for paragraph in header_cell.paragraphs for run in paragraph.runs if yasmin_project.identity.property_name in run.text)
    assert project_run.font.color.rgb is None

    recap_text = all_text(tmp_path / "Tableau_Recapitulatif.docx")
    for value in ("Appartement (Habitation)", "56", "16", "Garage", "15", "76", "4", "232"):
        assert value in recap_text
    regulation_rows = [[cell.text for cell in row.cells] for row in regulation.tables[9].rows]
    assert any("225" in row and "247" in row and "10000" in row for row in regulation_rows)
    regulation_xml_text = "".join(regulation.element.body.xpath(".//w:t/text()"))
    assert "Octobre 2025" in regulation_xml_text
    assert "October 2025" not in regulation_xml_text
    narrative_text = "\n".join(
        cell.text for table in regulation.tables[2:9] for row in table.rows for cell in row.cells
    )
    assert narrative_text.count("PARTIE PRIVATIVE N° 6-6a") == 1
    assert regulation.tables[5].rows[3].cells[0].text.strip() == yasmin_project.levels[2].name

    reference = Document(resource_root() / "templates" / "runtime" / "reglement.docx")
    is_article_one = lambda text: text.replace("\xa0", " ").strip().startswith("Article 1 :")
    reference_article = next(p.text for p in reference.paragraphs if is_article_one(p.text))
    generated_article = next(p.text for p in regulation.paragraphs if is_article_one(p.text))
    assert generated_article == reference_article
