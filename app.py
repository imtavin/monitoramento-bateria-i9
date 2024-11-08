from flask import Flask, render_template, request, redirect, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import plotly.graph_objs as go
from plotly.subplots import make_subplots

app = Flask(__name__)

TEMPERATURA_LIMITE = 40  
TENSAO_LIMITE = 13    

# Função para conexão ao banco de dados
def connect_db():
    conn = sqlite3.connect('bateria.db')
    return conn

# Função para obter baterias por localização
def get_batteries_by_location(location):
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT mac_address, company_name FROM batteries WHERE location = ?"
    cursor.execute(query, (location,))
    batteries = cursor.fetchall()
    conn.close()
    return batteries

# Função para obter os dados da bateria
def get_battery_data(filters=None):
    conn = connect_db()
    cursor = conn.cursor()

    # Aplica filtros, se houver
    query = "SELECT * FROM batteries WHERE 1=1"
    params = []

    if filters:
        if 'location' in filters:
            query += " AND location = ?"
            params.append(filters['location'])

        if 'voltage' in filters:
            query += " AND voltage < ?"
            params.append(filters['voltage'])

        if 'mac_address' in filters:
            query += " AND mac_address = ?"
            params.append(filters['mac_address'])

    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data

def fetch_battery_data():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT mac_address, company_name, location, resistance, voltage, temperature FROM batteries")
    data = cursor.fetchall()
    conn.close()
    return data

# Rota para gerar e baixar o relatório em PDF.
@app.route('/download-pdf')
def download_pdf():
    # Busca dados do banco
    baterias = fetch_battery_data()

    # Configura o PDF em memória
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Título do PDF
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 50, "Relatório de Status das Baterias")

    # Cabeçalhos da tabela
    pdf.setFont("Helvetica-Bold", 12)
    headers = ["MacAddress", "Empresa", "Localização", "Resistência (Ω)", "Tensão (V)", "Temperatura (°C)"]
    x_offset = 40
    y_offset = height - 100
    col_width = [100, 80, 80, 100, 70, 100]  # Define a largura de cada coluna para melhor organização

    # Desenha os cabeçalhos da tabela
    for i, header in enumerate(headers):
        pdf.drawString(x_offset, y_offset, header)
        x_offset += col_width[i]

    # Redefine o offset horizontal e ajusta o espaçamento vertical
    y_offset -= 25
    pdf.setFont("Helvetica", 10)

    # Adiciona dados na tabela
    for bateria in baterias:
        x_offset = 40  # Redefine o início da linha
        for i, item in enumerate(bateria):
            pdf.drawString(x_offset, y_offset, str(item) if item is not None else "N/A")
            x_offset += col_width[i]
        y_offset -= 15

        # Gera uma nova página se ultrapassar o limite da página
        if y_offset < 40:
            pdf.showPage()
            y_offset = height - 100
            # Redesenha cabeçalhos na nova página
            x_offset = 40
            pdf.setFont("Helvetica-Bold", 12)
            for i, header in enumerate(headers):
                pdf.drawString(x_offset, y_offset, header)
                x_offset += col_width[i]
            y_offset -= 25
            pdf.setFont("Helvetica", 10)

    # Finaliza e salva o PDF
    pdf.save()

    # Prepara o PDF para download
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="relatorio_baterias.pdf", mimetype='application/pdf')


# Função para cadastrar novas baterias
@app.route('/cadastro-bateria', methods=['GET', 'POST'])
def cadastro_bateria():
    if request.method == 'POST':
        company_name = request.form['company_name']
        mac_address = request.form['mac_address']
        location = request.form['location']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO batteries (company_name, mac_address, location) VALUES (?, ?, ?)", 
                       (company_name, mac_address, location))
        conn.commit()
        conn.close()

        return redirect('index')  # Redireciona para a página principal após o cadastro

    return render_template('cadastro_bateria.html')

def get_alerts (data):
    alerts = []  # Lista para armazenar mensagens de alerta
    
    for entry in data:
        temperatura = entry[6]
        tensao = entry[4]
        horario = entry[7]
        
        # Verifique se a temperatura excede o limite
        if temperatura > TEMPERATURA_LIMITE:
            print("ALERTA")
            alerts.append(f"Alerta: Temperatura alta de {temperatura}°C detectada no horario {horario}!")

        # Verifique se a tensão excede o limite
        if tensao > TENSAO_LIMITE:
            alerts.append(f"Alerta: Tensão alta de {tensao}V detectada no horario {horario}!")

    return alerts

# Função para criar os gráficos
def create_graphs(data):
    if not data:
        return "<p>Nenhum dado disponível</p>"

    data = sorted(data, key=lambda p: p[7], reverse=True)

    # Certifique-se de que os índices estão corretos, com base em como seu dataset está estruturado
    timestamps = [row[7] for row in data]  # Timestamp
    voltages = [row[4] for row in data]    # Voltage
    resistances = [row[5] for row in data] # Resistance
    temperatures = [row[6] for row in data] # Temperature (verifique se este índice é correto)

    if data and len(data) > 1 and len(data[1]) > 1:
        company = data[1][1]
    else:
        company = "Dados insuficientes"

    if data and len(data) > 1 and len(data[2]) > 1:
        mac_address = data[1][2]
    else:
        mac_address = "Dados insuficientes"

    print(data)

    fig = make_subplots(rows=3, cols=1, subplot_titles=('Voltage (V)', 'Resistance (Ω)', 'Temperature (°C)'))

    # Adiciona os dados ao gráfico
    fig.add_trace(go.Scatter(x=timestamps, y=voltages, mode='lines', name='Voltage'), row=1, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=resistances, mode='lines', name='Resistance'), row=2, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=temperatures, mode='lines', name='Temperature'), row=3, col=1)

    # Ajustar o layout
    fig.update_layout(height=900, title_text="Saúde da Bateria pelo MAC Address: " + mac_address + " Localizado em: " + company, showlegend=False)

    return fig.to_html(full_html=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    filters = {}
    batteries = []
    batteries_loc = []

    if request.method == 'POST':
        # Filtro por localização
        if request.form.get('location_filter'):
            filters['location'] = request.form['location_filter']

        # Filtro por tensão
        if request.form.get('voltage_filter'):
            filters['voltage'] = request.form['voltage_filter']

        # Filtro por MAC Address
        if request.form.get('mac_filter'):
            filters['mac_address'] = request.form['mac_filter']

        # Obter dados filtrados
        data = get_battery_data(filters)

        # Adicionando depuração para verificar os dados retornados
        # print(data)

        # Gerar lista de baterias (endereços MAC e empresas) para a localização filtrada
        if data:
            batteries = sorted(set([(row[2], row[1]) for row in data])) # (mac_address, company_name)
            batteries_loc = sorted(set([row[3] for row in data]))  # Lista única e ordenada de localizações
        
        # Verificar se um MAC Address foi selecionado
        if 'mac_address' in filters:
            graph = create_graphs(data)
            alerts = get_alerts(data)
        else:
            graph = "<p>Selecione um MAC Address para visualizar o gráfico.</p>"
            alerts = []

        return render_template('index.html', graph=graph, batteries=batteries, batteries_loc=batteries_loc, filters=filters, alerts=alerts)
    
    # Se for um GET (sem filtro), carrega todos os dados
    data = get_battery_data()
    graph = create_graphs(data)
    
    return render_template('index.html', graph=graph, batteries=batteries, batteries_loc=batteries_loc, filters=filters)


if __name__ == '__main__':
    app.run(debug=True)
