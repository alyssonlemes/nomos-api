import io
from datetime import datetime

import openpyxl
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.services.dashboard_service import coletar_estatisticas

CLIENT_STATUS_LABELS = {
    "active": "Ativo",
    "inactive": "Inativo",
    "prospect": "Prospecção",
    "archived": "Arquivado",
}
_FONTE = "Segoe UI"
_COLUNAS = "BCD"
_LARGURA_GRAFICO = 15


def _fonte(tamanho: int, **extra) -> Font:
    return Font(name=_FONTE, size=tamanho, **extra)


def _fill(cor: str) -> PatternFill:
    return PatternFill(start_color=cor, end_color=cor, fill_type="solid")


def _faixa(ws: Worksheet, row: int, texto: str, fonte: Font, fill: PatternFill, align: Alignment, altura: int, ate: str) -> int:
    ws.merge_cells(f"B{row}:{ate}{row}")
    cell = ws[f"B{row}"]
    cell.value = texto
    cell.font = fonte
    cell.fill = fill
    cell.alignment = align
    ws.row_dimensions[row].height = altura
    return row + 1


def _linha(ws: Worksheet, row: int, valores: tuple, fonte: Font, border: Border, aligns: tuple, fill: PatternFill | None, formatos: tuple, altura: int) -> None:
    for coluna, valor, align, formato in zip(_COLUNAS, valores, aligns, formatos, strict=True):
        cell = ws[f"{coluna}{row}"]
        cell.value = valor
        cell.font = fonte
        cell.border = border
        cell.alignment = align
        if fill is not None and fill.fill_type:
            cell.fill = fill
        if formato:
            cell.number_format = formato
    ws.row_dimensions[row].height = altura


def _grafico_colunas(ws: Worksheet, titulo: str, cor: str, header_row: int, data_start: int, data_end: int, ancora: str) -> None:
    chart = BarChart()
    chart.type = "col"
    chart.style = 2
    chart.title = titulo
    chart.height = 7.5
    chart.width = 13.5
    chart.gapWidth = 180
    chart.legend = None
    chart.add_data(Reference(ws, min_col=3, min_row=header_row, max_row=data_end), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, min_row=data_start, max_row=data_end))
    if chart.series:
        chart.series[0].graphicalProperties.solidFill = cor
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True
    ws.add_chart(chart, ancora)


def _grafico_pizza(ws: Worksheet, titulo: str, cores: list[str], quantidade: int, header_row: int, data_start: int, data_end: int, ancora: str) -> None:
    chart = PieChart()
    chart.title = titulo
    chart.style = 10
    chart.height = 7.5
    chart.width = 13.5
    chart.add_data(Reference(ws, min_col=3, min_row=header_row, max_row=data_end), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, min_row=data_start, max_row=data_end))
    if chart.series:
        for indice in range(quantidade):
            ponto = DataPoint(idx=indice)
            ponto.graphicalProperties.solidFill = cores[indice % len(cores)]
            chart.series[0].data_points.append(ponto)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showPercent = True
    chart.dataLabels.showVal = False
    if chart.legend:
        chart.legend.legendPos = "r"
    ws.add_chart(chart, ancora)


def _distribuicao(
    ws: Worksheet,
    row: int,
    *,
    titulo: str,
    cabecalhos: tuple[str, str, str],
    itens: list[tuple[str, int]],
    rotulo_total: str,
    vazio: str | None,
    estilos: dict,
    titulo_grafico: str,
    grafico: str,
    cor: str | None = None,
    cores: list[str] | None = None,
    reservar_grafico: bool = True,
) -> int:
    if not itens and vazio is None:
        return row

    inicio = row
    row = _faixa(ws, row, titulo, estilos["sec"], estilos["sec_fill"], estilos["indent"], 24, "D")
    _linha(ws, row, cabecalhos, estilos["hdr"], estilos["border"], estilos["align_num"], estilos["hdr_fill"], ("", "", ""), 22)
    header_row = row
    row += 1
    data_start = row

    if itens:
        total_row = data_start + len(itens)
        for indice, (nome, quantidade) in enumerate(itens):
            fundo = estilos["alt"] if indice % 2 == 1 else estilos["none"]
            _linha(
                ws,
                row,
                (nome, quantidade, f"=C{row}/$C${total_row}"),
                estilos["data"],
                estilos["border"],
                estilos["align_num"],
                fundo,
                ("", "#,##0", "0.0%"),
                20,
            )
            row += 1
        data_end = row - 1
        _linha(
            ws,
            row,
            (rotulo_total, f"=SUM(C{data_start}:C{data_end})", f"=SUM(D{data_start}:D{data_end})"),
            estilos["total"],
            estilos["border_total"],
            estilos["align_num"],
            estilos["total_fill"],
            ("", "#,##0", "0.0%"),
            22,
        )
        row += 1
        ancora = f"F{inicio}"
        if grafico == "pizza":
            _grafico_pizza(ws, titulo_grafico, cores or [], len(itens), header_row, data_start, data_end, ancora)
        else:
            _grafico_colunas(ws, titulo_grafico, cor or "0284C7", header_row, data_start, data_end, ancora)
    else:
        ws.merge_cells(f"B{row}:D{row}")
        cell = ws[f"B{row}"]
        cell.value = vazio
        cell.font = estilos["vazio"]
        cell.alignment = estilos["center"]
        cell.border = estilos["border"]
        row += 1

    if reservar_grafico:
        return max(row, inicio + _LARGURA_GRAFICO) + 2
    return row


def gerar_planilha(
    db: Session,
    current_user: User,
    organization_id: int,
    filter_user_id: int | None,
) -> tuple[bytes, str]:
    stats = coletar_estatisticas(db, current_user, organization_id, filter_user_id)
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    org_name = org.name if org else "Organização Nomos"
    now = datetime.now()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dashboard & Gráficos"
    ws.views.sheetView[0].showGridLines = True
    for coluna, largura in {"A": 4, "B": 30, "C": 16, "D": 18, "E": 4, "F": 16, "G": 16, "H": 16, "I": 16, "J": 16, "K": 16, "L": 4}.items():
        ws.column_dimensions[coluna].width = largura

    thin = Side(style="thin", color="E2E8F0")
    left = Alignment(horizontal="left", vertical="center")
    right = Alignment(horizontal="right", vertical="center")
    estilos = {
        "sec": _fonte(11, bold=True, color="FFFFFF"),
        "sec_fill": _fill("334155"),
        "indent": Alignment(vertical="center", indent=1),
        "hdr": _fonte(9, bold=True, color="FFFFFF"),
        "hdr_fill": _fill("475569"),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "border_total": Border(left=thin, right=thin, top=thin, bottom=Side(style="double", color="1E293B")),
        "align_hdr": (left, right, left),
        "align_num": (left, right, right),
        "data": _fonte(9),
        "alt": _fill("F8FAFC"),
        "none": PatternFill(fill_type=None),
        "total": _fonte(9, bold=True, color="0F172A"),
        "total_fill": _fill("F1F5F9"),
        "vazio": _fonte(9, italic=True, color="64748B"),
        "center": Alignment(horizontal="center", vertical="center"),
    }

    row = 2
    row = _faixa(ws, row, "NOMOS — SISTEMA DE GESTÃO JURÍDICA", _fonte(14, bold=True, color="FFFFFF"), _fill("0F172A"), estilos["center"], 32, "K")
    row = _faixa(ws, row, "Relatório Geral da Dashboard com Gráficos Dinâmicos e Indicadores", _fonte(10, italic=True, color="E2E8F0"), _fill("1E293B"), estilos["center"], 22, "K")
    row = _faixa(ws, row, f"Organização: {org_name} | Emissão: {now.strftime('%d/%m/%Y às %H:%M')}", _fonte(9, color="64748B"), _fill("F8FAFC"), estilos["center"], 20, "K")
    row += 1

    row = _faixa(ws, row, "1. INDICADORES PRINCIPAIS (KPIs)", estilos["sec"], estilos["sec_fill"], estilos["indent"], 24, "D")
    _linha(ws, row, ("Indicador Operacional", "Total", "Referência"), estilos["hdr"], estilos["border"], estilos["align_hdr"], estilos["hdr_fill"], ("", "", ""), 22)
    row += 1
    kpis = [
        ("Total de Clientes Cadastrados", stats.total_clients, "Base Total"),
        ("Processos Jurídicos Ativos", stats.total_legal_actions, "Em Andamento"),
        ("Novos Clientes (30 dias)", stats.recent_clients_30d, "Últimos 30 dias"),
        ("Novas Ações (30 dias)", stats.recent_actions_30d, "Últimos 30 dias"),
        ("Usuários na Organização", stats.total_users, "Equipe Ativa"),
    ]
    for indice, item in enumerate(kpis):
        _linha(
            ws, row, item, estilos["data"], estilos["border"], estilos["align_hdr"],
            estilos["alt"] if indice % 2 == 1 else estilos["none"], ("", "#,##0", ""), 20,
        )
        ws[f"C{row}"].font = _fonte(9, bold=True)
        row += 1
    row += 2

    row = _distribuicao(
        ws, row,
        titulo="2. PROCESSOS POR STATUS",
        titulo_grafico="Processos por Status",
        cabecalhos=("Status Processual", "Processos", "Participação (%)"),
        itens=list((stats.actions_by_status or {}).items()),
        rotulo_total="Total de Processos",
        vazio="Nenhum processo cadastrado",
        estilos=estilos,
        grafico="colunas",
        cor="0284C7",
    )
    clientes = [
        (CLIENT_STATUS_LABELS.get(chave, chave), quantidade)
        for chave, quantidade in (stats.clients_by_status or {}).items()
    ]
    row = _distribuicao(
        ws, row,
        titulo="3. CLIENTES POR STATUS",
        titulo_grafico="Clientes por Status",
        cabecalhos=("Status do Cliente", "Clientes", "Participação (%)"),
        itens=clientes,
        rotulo_total="Total de Clientes",
        vazio="Nenhum cliente cadastrado",
        estilos=estilos,
        grafico="pizza",
        cores=["0284C7", "0EA5E9", "38BDF8", "6366F1", "8B5CF6", "EC4899", "F59E0B", "10B981"],
    )
    _distribuicao(
        ws, row,
        titulo="4. PROCESSOS POR TIPO DE AÇÃO",
        titulo_grafico="Processos por Tipo de Ação",
        cabecalhos=("Tipo de Ação", "Processos", "Participação (%)"),
        itens=list((stats.actions_by_type or {}).items()),
        rotulo_total="Total de Ações por Tipo",
        vazio=None,
        estilos=estilos,
        grafico="colunas",
        cor="6366F1",
        reservar_grafico=False,
    )

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue(), f"relatorio-dashboard-nomos_{now.strftime('%Y-%m-%d_%H%M')}.xlsx"
