import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint

from app.database import get_db
from app.schemas.dashboard import DashboardStats
from app.models.user import User
from app.models.client import Client
from app.models.organization import Organization
from app.models.legal_action import LegalAction
from app.models.legal_action_type import LegalActionType
from app.models.legal_action_status import LegalActionStatus
from app.api.deps import get_current_active_user, get_user_organization, require_legal_actions_access, get_data_filter_user_id

router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Obter estatísticas do dashboard"
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
    organization_id: int = Depends(get_user_organization),
    filter_user_id: int | None = Depends(get_data_filter_user_id)
):
    """
    Retorna estatísticas consolidadas para o dashboard
    
    Inclui:
    - Total de clientes, ações e usuários
    - Distribuição de ações por status e tipo
    - Distribuição de clientes por status
    - Novos registros nos últimos 30 dias
    
    - ADMIN/OWNER: Veem estatísticas de toda a organização
    - MEMBER/VIEWER: Veem apenas suas próprias estatísticas
    """
    # Data de 30 dias atrás
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Total de clientes
    total_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id
    )
    if filter_user_id:
        total_clients = total_clients.filter(Client.user_id == filter_user_id)
    total_clients = total_clients.scalar()
    
    # Total de ações jurídicas
    total_legal_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id
    )
    if filter_user_id:
        total_legal_actions = total_legal_actions.filter(LegalAction.user_id == filter_user_id)
    total_legal_actions = total_legal_actions.scalar()
    
    # Total de usuários da organização (sempre mostra o mesmo - não filtra por user)
    total_users = db.query(func.count(User.id)).filter(
        User.organization_id == organization_id
    ).scalar()
    
    # Ações por status (nome do status do catálogo)
    actions_by_status_query = (
        db.query(LegalActionStatus.name, func.count(LegalAction.id))
        .join(LegalAction, LegalAction.legal_status_id == LegalActionStatus.id)
        .filter(LegalAction.organization_id == organization_id)
    )
    if filter_user_id:
        actions_by_status_query = actions_by_status_query.filter(LegalAction.user_id == filter_user_id)
    actions_by_status_query = actions_by_status_query.group_by(LegalActionStatus.id, LegalActionStatus.name).all()
    actions_by_status = {name: count for name, count in actions_by_status_query}
    
    # Ações por tipo (nome do tipo do catálogo)
    actions_by_type_query = (
        db.query(LegalActionType.name, func.count(LegalAction.id))
        .join(LegalAction, LegalAction.action_type_id == LegalActionType.id)
        .filter(LegalAction.organization_id == organization_id)
    )
    if filter_user_id:
        actions_by_type_query = actions_by_type_query.filter(LegalAction.user_id == filter_user_id)
    actions_by_type_query = actions_by_type_query.group_by(LegalActionType.id, LegalActionType.name).all()
    actions_by_type = {name: count for name, count in actions_by_type_query}
    
    # Clientes por status
    clients_by_status_query = db.query(
        Client.status,
        func.count(Client.id)
    ).filter(
        Client.organization_id == organization_id
    )
    if filter_user_id:
        clients_by_status_query = clients_by_status_query.filter(Client.user_id == filter_user_id)
    clients_by_status_query = clients_by_status_query.group_by(Client.status).all()
    clients_by_status = {status: count for status, count in clients_by_status_query}
    
    # Clientes criados nos últimos 30 dias
    recent_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id,
        Client.created_at >= thirty_days_ago
    )
    if filter_user_id:
        recent_clients = recent_clients.filter(Client.user_id == filter_user_id)
    recent_clients = recent_clients.scalar()
    
    # Ações criadas nos últimos 30 dias
    recent_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id,
        LegalAction.created_at >= thirty_days_ago
    )
    if filter_user_id:
        recent_actions = recent_actions.filter(LegalAction.user_id == filter_user_id)
    recent_actions = recent_actions.scalar()
    
    return DashboardStats(
        total_clients=total_clients or 0,
        total_legal_actions=total_legal_actions or 0,
        total_users=total_users or 0,
        actions_by_status=actions_by_status,
        actions_by_type=actions_by_type,
        clients_by_status=clients_by_status,
        recent_clients_30d=recent_clients or 0,
        recent_actions_30d=recent_actions or 0
    )


CLIENT_STATUS_LABELS = {
    "active": "Ativo",
    "inactive": "Inativo",
    "prospect": "Prospecção",
    "archived": "Arquivado",
}


@router.get(
    "/export-excel",
    summary="Exportar planilha Excel com gráficos nativos dinâmicos"
)
def export_dashboard_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
    organization_id: int = Depends(get_user_organization),
    filter_user_id: int | None = Depends(get_data_filter_user_id)
):
    """
    Gera e exporta uma planilha Excel (.xlsx) contendo tabelas analíticas e
    gráficos NATIVOS e DINÂMICOS do Excel (BarChart e PieChart via DrawingML).
    Ao alterar os dados nas células, os gráficos no Excel se atualizam automaticamente.
    """
    # 1. Coleta de dados
    stats = get_dashboard_stats(db, current_user, organization_id, filter_user_id)
    
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    org_name = org.name if org else "Organização Nomos"
    
    now = datetime.now()
    formatted_date = now.strftime("%d/%m/%Y às %H:%M")
    file_date_str = now.strftime("%Y-%m-%d_%H%M")
    
    # 2. Criação do Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dashboard & Gráficos"
    ws.views.sheetView[0].showGridLines = True
    
    # Larguras das colunas
    col_widths = {
        'A': 4,
        'B': 30,
        'C': 16,
        'D': 18,
        'E': 4,
        'F': 16,
        'G': 16,
        'H': 16,
        'I': 16,
        'J': 16,
        'K': 16,
        'L': 4
    }
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    # Estilos
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    meta_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    sec_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    tbl_hdr_fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
    total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    font_white_bold_14 = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    font_white_italic_10 = Font(name="Segoe UI", size=10, italic=True, color="E2E8F0")
    font_meta = Font(name="Segoe UI", size=9, color="64748B")
    font_sec = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_tbl_hdr = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=9)
    font_total = Font(name="Segoe UI", size=9, bold=True, color="0F172A")

    thin_border_side = Side(style="thin", color="E2E8F0")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    double_bottom_side = Side(style="double", color="1E293B")
    border_total = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_bottom_side)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    r = 2
    # Banner Principal
    ws.merge_cells(f"B{r}:K{r}")
    c = ws[f"B{r}"]
    c.value = "NOMOS — SISTEMA DE GESTÃO JURÍDICA"
    c.font = font_white_bold_14
    c.fill = header_fill
    c.alignment = align_center
    ws.row_dimensions[r].height = 32
    r += 1

    ws.merge_cells(f"B{r}:K{r}")
    c = ws[f"B{r}"]
    c.value = "Relatório Geral da Dashboard com Gráficos Dinâmicos e Indicadores"
    c.font = font_white_italic_10
    c.fill = sub_fill
    c.alignment = align_center
    ws.row_dimensions[r].height = 22
    r += 1

    ws.merge_cells(f"B{r}:K{r}")
    c = ws[f"B{r}"]
    c.value = f"Organização: {org_name} | Emissão: {formatted_date}"
    c.font = font_meta
    c.fill = meta_fill
    c.alignment = align_center
    ws.row_dimensions[r].height = 20
    r += 2

    # SEÇÃO 1: KPIs
    ws.merge_cells(f"B{r}:D{r}")
    c = ws[f"B{r}"]
    c.value = "1. INDICADORES PRINCIPAIS (KPIs)"
    c.font = font_sec
    c.fill = sec_fill
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[r].height = 24
    r += 1

    # Cabeçalho KPIs
    kpi_headers = ["Indicador Operacional", "Total", "Referência"]
    for idx, h in enumerate(kpi_headers):
        col_letter = ["B", "C", "D"][idx]
        cell = ws[f"{col_letter}{r}"]
        cell.value = h
        cell.font = font_tbl_hdr
        cell.fill = tbl_hdr_fill
        cell.alignment = align_right if col_letter == "C" else align_left
        cell.border = border_cell
    ws.row_dimensions[r].height = 22
    r += 1

    kpis = [
        ("Total de Clientes Cadastrados", stats.total_clients, "Base Total"),
        ("Processos Jurídicos Ativos", stats.total_legal_actions, "Em Andamento"),
        ("Novos Clientes (30 dias)", stats.recent_clients_30d, "Últimos 30 dias"),
        ("Novas Ações (30 dias)", stats.recent_actions_30d, "Últimos 30 dias"),
        ("Usuários na Organização", stats.total_users, "Equipe Ativa"),
    ]
    for idx, (label, val, ref) in enumerate(kpis):
        bg = alt_fill if idx % 2 == 1 else PatternFill(fill_type=None)
        
        ws[f"B{r}"].value = label
        ws[f"C{r}"].value = val
        ws[f"C{r}"].number_format = "#,##0"
        ws[f"D{r}"].value = ref
        
        for col_letter in ["B", "C", "D"]:
            cell = ws[f"{col_letter}{r}"]
            cell.font = Font(name="Segoe UI", size=9, bold=(col_letter == "C"))
            if bg.fill_type:
                cell.fill = bg
            cell.border = border_cell
            cell.alignment = align_right if col_letter == "C" else align_left
        ws.row_dimensions[r].height = 20
        r += 1

    r += 2

    # SEÇÃO 2: PROCESSOS POR STATUS (Com Gráfico Dinâmico)
    status_sec_start = r
    ws.merge_cells(f"B{r}:D{r}")
    c = ws[f"B{r}"]
    c.value = "2. PROCESSOS POR STATUS"
    c.font = font_sec
    c.fill = sec_fill
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[r].height = 24
    r += 1

    ws[f"B{r}"].value = "Status Processual"
    ws[f"C{r}"].value = "Processos"
    ws[f"D{r}"].value = "Participação (%)"
    for col_letter in ["B", "C", "D"]:
        cell = ws[f"{col_letter}{r}"]
        cell.font = font_tbl_hdr
        cell.fill = tbl_hdr_fill
        cell.alignment = align_right if col_letter in ["C", "D"] else align_left
        cell.border = border_cell
    ws.row_dimensions[r].height = 22
    
    status_table_header_row = r
    r += 1
    status_data_start_row = r

    actions_items = list((stats.actions_by_status or {}).items())
    if actions_items:
        total_row_num = status_data_start_row + len(actions_items)
        for idx, (status_name, count) in enumerate(actions_items):
            curr_row = r
            bg = alt_fill if idx % 2 == 1 else PatternFill(fill_type=None)
            
            ws[f"B{curr_row}"].value = status_name
            ws[f"C{curr_row}"].value = count
            ws[f"C{curr_row}"].number_format = "#,##0"
            # Fórmula dinâmica no Excel!
            ws[f"D{curr_row}"].value = f"=C{curr_row}/$C${total_row_num}"
            ws[f"D{curr_row}"].number_format = "0.0%"
            
            for col_letter in ["B", "C", "D"]:
                cell = ws[f"{col_letter}{curr_row}"]
                cell.font = font_data
                if bg.fill_type:
                    cell.fill = bg
                cell.border = border_cell
                cell.alignment = align_right if col_letter in ["C", "D"] else align_left
            ws.row_dimensions[curr_row].height = 20
            r += 1
        
        status_data_end_row = r - 1

        # Linha de Total com Fórmula
        ws[f"B{r}"].value = "Total de Processos"
        ws[f"C{r}"].value = f"=SUM(C{status_data_start_row}:C{status_data_end_row})"
        ws[f"C{r}"].number_format = "#,##0"
        ws[f"D{r}"].value = f"=SUM(D{status_data_start_row}:D{status_data_end_row})"
        ws[f"D{r}"].number_format = "0.0%"
        
        for col_letter in ["B", "C", "D"]:
            cell = ws[f"{col_letter}{r}"]
            cell.font = font_total
            cell.fill = total_fill
            cell.border = border_total
            cell.alignment = align_right if col_letter in ["C", "D"] else align_left
        ws.row_dimensions[r].height = 22
        r += 1

        # GRÁFICO DINÂMICO NATIVO: BARCHART (Colunas Verticais Elegantes)
        bar_chart = BarChart()
        bar_chart.type = "col"
        bar_chart.style = 2
        bar_chart.title = "Processos por Status"
        bar_chart.height = 7.5
        bar_chart.width = 13.5
        bar_chart.gapWidth = 180
        bar_chart.legend = None

        data_ref = Reference(ws, min_col=3, min_row=status_table_header_row, max_row=status_data_end_row)
        cats_ref = Reference(ws, min_col=2, min_row=status_data_start_row, max_row=status_data_end_row)
        bar_chart.add_data(data_ref, titles_from_data=True)
        bar_chart.set_categories(cats_ref)
        
        if bar_chart.series:
            bar_chart.series[0].graphicalProperties.solidFill = "0284C7"
        
        bar_chart.dataLabels = DataLabelList()
        bar_chart.dataLabels.showVal = True
        
        ws.add_chart(bar_chart, f"F{status_sec_start}")
    else:
        ws.merge_cells(f"B{r}:D{r}")
        cell = ws[f"B{r}"]
        cell.value = "Nenhum processo cadastrado"
        cell.font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
        cell.alignment = align_center
        cell.border = border_cell
        r += 1

    # Espaçamento proporcional para o gráfico
    r = max(r, status_sec_start + 15)
    r += 2

    # SEÇÃO 3: CLIENTES POR STATUS (Com Gráfico Dinâmico de Pizza)
    client_sec_start = r
    ws.merge_cells(f"B{r}:D{r}")
    c = ws[f"B{r}"]
    c.value = "3. CLIENTES POR STATUS"
    c.font = font_sec
    c.fill = sec_fill
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[r].height = 24
    r += 1

    ws[f"B{r}"].value = "Status do Cliente"
    ws[f"C{r}"].value = "Clientes"
    ws[f"D{r}"].value = "Participação (%)"
    for col_letter in ["B", "C", "D"]:
        cell = ws[f"{col_letter}{r}"]
        cell.font = font_tbl_hdr
        cell.fill = tbl_hdr_fill
        cell.alignment = align_right if col_letter in ["C", "D"] else align_left
        cell.border = border_cell
    ws.row_dimensions[r].height = 22
    
    client_table_header_row = r
    r += 1
    client_data_start_row = r

    client_items = list((stats.clients_by_status or {}).items())
    if client_items:
        total_client_row_num = client_data_start_row + len(client_items)
        for idx, (status_key, count) in enumerate(client_items):
            curr_row = r
            bg = alt_fill if idx % 2 == 1 else PatternFill(fill_type=None)
            status_label = CLIENT_STATUS_LABELS.get(status_key, status_key)
            
            ws[f"B{curr_row}"].value = status_label
            ws[f"C{curr_row}"].value = count
            ws[f"C{curr_row}"].number_format = "#,##0"
            ws[f"D{curr_row}"].value = f"=C{curr_row}/$C${total_client_row_num}"
            ws[f"D{curr_row}"].number_format = "0.0%"
            
            for col_letter in ["B", "C", "D"]:
                cell = ws[f"{col_letter}{curr_row}"]
                cell.font = font_data
                if bg.fill_type:
                    cell.fill = bg
                cell.border = border_cell
                cell.alignment = align_right if col_letter in ["C", "D"] else align_left
            ws.row_dimensions[curr_row].height = 20
            r += 1
        
        client_data_end_row = r - 1

        # Linha de Total com Fórmula
        ws[f"B{r}"].value = "Total de Clientes"
        ws[f"C{r}"].value = f"=SUM(C{client_data_start_row}:C{client_data_end_row})"
        ws[f"C{r}"].number_format = "#,##0"
        ws[f"D{r}"].value = f"=SUM(D{client_data_start_row}:D{client_data_end_row})"
        ws[f"D{r}"].number_format = "0.0%"
        
        for col_letter in ["B", "C", "D"]:
            cell = ws[f"{col_letter}{r}"]
            cell.font = font_total
            cell.fill = total_fill
            cell.border = border_total
            cell.alignment = align_right if col_letter in ["C", "D"] else align_left
        ws.row_dimensions[r].height = 22
        r += 1

        # GRÁFICO DINÂMICO NATIVO: PIECHART (Pizza)
        pie_chart = PieChart()
        pie_chart.title = "Clientes por Status"
        pie_chart.style = 10
        pie_chart.height = 7.5
        pie_chart.width = 13.5

        data_ref_pie = Reference(ws, min_col=3, min_row=client_table_header_row, max_row=client_data_end_row)
        cats_ref_pie = Reference(ws, min_col=2, min_row=client_data_start_row, max_row=client_data_end_row)
        pie_chart.add_data(data_ref_pie, titles_from_data=True)
        pie_chart.set_categories(cats_ref_pie)
        
        # Cores customizadas harmoniosas para as fatias
        pie_colors = ["0284C7", "0EA5E9", "38BDF8", "6366F1", "8B5CF6", "EC4899", "F59E0B", "10B981"]
        if pie_chart.series:
            for idx in range(len(client_items)):
                dp = DataPoint(idx=idx)
                dp.graphicalProperties.solidFill = pie_colors[idx % len(pie_colors)]
                pie_chart.series[0].data_points.append(dp)
        
        pie_chart.dataLabels = DataLabelList()
        pie_chart.dataLabels.showPercent = True
        pie_chart.dataLabels.showVal = False
        if pie_chart.legend:
            pie_chart.legend.legendPos = "r"
        
        ws.add_chart(pie_chart, f"F{client_sec_start}")
    else:
        ws.merge_cells(f"B{r}:D{r}")
        cell = ws[f"B{r}"]
        cell.value = "Nenhum cliente cadastrado"
        cell.font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
        cell.alignment = align_center
        cell.border = border_cell
        r += 1

    r = max(r, client_sec_start + 15)
    r += 2

    # SEÇÃO 4: PROCESSOS POR TIPO DE AÇÃO (Com Gráfico Dinâmico de Colunas)
    type_items = list((stats.actions_by_type or {}).items())
    if type_items:
        type_sec_start = r
        ws.merge_cells(f"B{r}:D{r}")
        c = ws[f"B{r}"]
        c.value = "4. PROCESSOS POR TIPO DE AÇÃO"
        c.font = font_sec
        c.fill = sec_fill
        c.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[r].height = 24
        r += 1

        ws[f"B{r}"].value = "Tipo de Ação"
        ws[f"C{r}"].value = "Processos"
        ws[f"D{r}"].value = "Participação (%)"
        for col_letter in ["B", "C", "D"]:
            cell = ws[f"{col_letter}{r}"]
            cell.font = font_tbl_hdr
            cell.fill = tbl_hdr_fill
            cell.alignment = align_right if col_letter in ["C", "D"] else align_left
            cell.border = border_cell
        ws.row_dimensions[r].height = 22
        
        type_table_header_row = r
        r += 1
        type_data_start_row = r

        total_type_row_num = type_data_start_row + len(type_items)
        for idx, (type_name, count) in enumerate(type_items):
            curr_row = r
            bg = alt_fill if idx % 2 == 1 else PatternFill(fill_type=None)
            
            ws[f"B{curr_row}"].value = type_name
            ws[f"C{curr_row}"].value = count
            ws[f"C{curr_row}"].number_format = "#,##0"
            ws[f"D{curr_row}"].value = f"=C{curr_row}/$C${total_type_row_num}"
            ws[f"D{curr_row}"].number_format = "0.0%"
            
            for col_letter in ["B", "C", "D"]:
                cell = ws[f"{col_letter}{curr_row}"]
                cell.font = font_data
                if bg.fill_type:
                    cell.fill = bg
                cell.border = border_cell
                cell.alignment = align_right if col_letter in ["C", "D"] else align_left
            ws.row_dimensions[curr_row].height = 20
            r += 1
        
        type_data_end_row = r - 1

        # Linha de Total com Fórmula
        ws[f"B{r}"].value = "Total de Ações por Tipo"
        ws[f"C{r}"].value = f"=SUM(C{type_data_start_row}:C{type_data_end_row})"
        ws[f"C{r}"].number_format = "#,##0"
        ws[f"D{r}"].value = f"=SUM(D{type_data_start_row}:D{type_data_end_row})"
        ws[f"D{r}"].number_format = "0.0%"
        
        for col_letter in ["B", "C", "D"]:
            cell = ws[f"{col_letter}{r}"]
            cell.font = font_total
            cell.fill = total_fill
            cell.border = border_total
            cell.alignment = align_right if col_letter in ["C", "D"] else align_left
        ws.row_dimensions[r].height = 22
        r += 1

        # GRÁFICO DINÂMICO NATIVO: COLUNAS
        type_chart = BarChart()
        type_chart.type = "col"
        type_chart.style = 2
        type_chart.title = "Processos por Tipo de Ação"
        type_chart.height = 7.5
        type_chart.width = 13.5
        type_chart.gapWidth = 180
        type_chart.legend = None

        data_ref_type = Reference(ws, min_col=3, min_row=type_table_header_row, max_row=type_data_end_row)
        cats_ref_type = Reference(ws, min_col=2, min_row=type_data_start_row, max_row=type_data_end_row)
        type_chart.add_data(data_ref_type, titles_from_data=True)
        type_chart.set_categories(cats_ref_type)
        
        if type_chart.series:
            type_chart.series[0].graphicalProperties.solidFill = "6366F1"
        
        type_chart.dataLabels = DataLabelList()
        type_chart.dataLabels.showVal = True
        
        ws.add_chart(type_chart, f"F{type_sec_start}")

    # 3. Gerar stream de bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"relatorio-dashboard-nomos_{file_date_str}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )

