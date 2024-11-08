from flask import Flask, render_template, request, redirect, send_file, url_for, Response
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from io import BytesIO
import sqlite3
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from io import BytesIO
from werkzeug.security import generate_password_hash

app = Flask(__name__)

TEMPERATURA_LIMITE = 40  
TENSAO_LIMITE = 13    

# Função para conexão ao banco de dados
def connect_db():
    conn = sqlite3.connect('bateria.db')
    return conn

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
    baterias = fetch_battery_data()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # PDF Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 50, "Relatório de Status das Baterias")

    # Column headers and widths
    headers = ["MacAddress", "Empresa", "Localização", "Resistência (Ω)", "Tensão (V)", "Temperatura (°C)", "Data/Hora"]
    col_widths = [90, 80, 80, 80, 70, 90, 100]  # Adjusted column widths
    x_offset_start = 30
    y_offset = height - 100
    row_height = 20

    # Draw headers
    pdf.setFont("Helvetica-Bold", 10)
    x_offset = x_offset_start
    for i, header in enumerate(headers):
        pdf.drawString(x_offset, y_offset, header)
        x_offset += col_widths[i]

    y_offset -= row_height

    # Draw data rows
    pdf.setFont("Helvetica", 9)
    for bateria in baterias:
        x_offset = x_offset_start
        for i, item in enumerate(bateria):
            text = str(item) if item is not None else "N/A"
            pdf.drawString(x_offset, y_offset, text)
            x_offset += col_widths[i]
        
        y_offset -= row_height

        # Create a new page if nearing the end of the current page
        if y_offset < 50:
            pdf.showPage()
            y_offset = height - 100
            
            # Redraw headers on new page
            pdf.setFont("Helvetica-Bold", 10)
            x_offset = x_offset_start
            for i, header in enumerate(headers):
                pdf.drawString(x_offset, y_offset, header)
                x_offset += col_widths[i]
            
            y_offset -= row_height
            pdf.setFont("Helvetica", 9)

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="relatorio_baterias.pdf", mimetype='application/pdf')

@app.route('/cadastro-usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        conn.close()
    return render_template('cadastro_usuario.html')

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
    conn = connect_db()
    cursor = conn.cursor()
    alerts = []  # Lista para armazenar mensagens de alerta
    
    for entry in data:
        temperature = entry[6]
        timestamp = entry[7]
        voltage = entry[4]
        location = entry[3]
        mac_address = entry[2]
        
        # Verifica se um alerta de temperatura já foi registrado recentemente
        if temperature > TEMPERATURA_LIMITE:
            cursor.execute('''
                SELECT * FROM alerts_log 
                WHERE mac_address = ? AND category = 'Temperatura' 
                AND alert_time > datetime('now', '-1 hour')
            ''', (mac_address,))
            existing_alert = cursor.fetchone()

            if not existing_alert:
                alert_message = f"Temperatura alta: {temperature}°C detectada no horario {timestamp}!"
                alerts.append(alert_message)
                cursor.execute('''
                    INSERT INTO alerts_log (mac_address, alert_message, category, alert_time, location)
                    VALUES (?, ?, ?, ?, ?)
                ''', (mac_address, alert_message, "Temperatura", timestamp, location))

        # Verifica se um alerta de tensão já foi registrado recentemente
        if voltage > TENSAO_LIMITE:
            cursor.execute('''
                SELECT * FROM alerts_log 
                WHERE mac_address = ? AND category = 'Tensão' 
                AND alert_time > datetime('now', '-1 hour')
            ''', (mac_address,))
            existing_alert = cursor.fetchone()

            if not existing_alert:
                alert_message = f"Tensão alta: {voltage}V detectada no horario {timestamp}!"
                alerts.append(alert_message)
                cursor.execute('''
                    INSERT INTO alerts_log (mac_address, alert_message, category, alert_time, location)
                    VALUES (?, ?, ?, ?, ?)
                ''', (mac_address, alert_message, "Tensão", timestamp, location))

    conn.commit()
    conn.close()
    return alerts

# Função para criar os gráficos
def create_graphs(data):
    if not data:
        return "<p>Nenhum dado disponível</p>"

    data = sorted(data, key=lambda p: p[7], reverse=True)

    timestamps = [row[7] for row in data]  # Timestamp
    voltages = [row[4] for row in data]    # Voltage
    resistances = [row[5] for row in data] # Resistance
    temperatures = [row[6] for row in data] # Temperature

    if data and len(data) > 1 and len(data[1]) > 1:
        company = data[1][1]
    else:
        company = "Dados insuficientes"

    fig = make_subplots(rows=3, cols=1, subplot_titles=('Voltage (V)', 'Resistance (Ω)', 'Temperature (°C)'))

    fig.add_trace(go.Scatter(x=timestamps, y=voltages, mode='lines', name='Voltage'), row=1, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=resistances, mode='lines', name='Resistance'), row=2, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=temperatures, mode='lines', name='Temperature'), row=3, col=1)

    fig.update_layout(height=900, title_text="Saúde da Bateria", showlegend=False)

    return fig.to_html(full_html=False)

# Função para gerar o PDF do relatório
@app.route('/gerar-relatorio', methods=['GET'])
def gerar_relatorio():
    # Obter os filtros, se existirem
    filters = request.args  # Obtém os filtros da URL (por exemplo, localização, tensão, etc.)
    data = get_battery_data(filters)  # Obtém os dados da bateria de acordo com os filtros

    # Criar o PDF em memória
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Definir título do relatório
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Relatório de Bateria - Dados de Saúde")

    # Inserir os dados do gráfico no PDF
    y_position = 730  # Posição inicial do texto

    c.setFont("Helvetica", 12)
    for entry in data:
        mac_address = entry[2]
        company = entry[1]
        location = entry[3]
        voltage = entry[4]
        temperature = entry[6]
        timestamp = entry[7]

        # Adiciona informações ao PDF
        c.drawString(100, y_position, f"MAC Address: {mac_address}")
        c.drawString(100, y_position - 20, f"Localização: {location}")
        c.drawString(100, y_position - 40, f"Empresa: {company}")
        c.drawString(100, y_position - 60, f"Tensão: {voltage}V")
        c.drawString(100, y_position - 80, f"Temperatura: {temperature}°C")
        c.drawString(100, y_position - 100, f"Horário: {timestamp}")

        y_position -= 120  # Ajusta a posição vertical para a próxima entrada

        if y_position < 100:  # Se a página estiver quase cheia, cria uma nova página
            c.showPage()
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 750, "Relatório de Bateria - Dados de Saúde")
            y_position = 730  # Reseta a posição para a nova página

    # Salva o PDF no buffer
    c.save()

    # Rewind do buffer para leitura
    buffer.seek(0)

    # Envia o PDF como resposta para download
    return Response(buffer, mimetype='application/pdf', headers={"Content-Disposition": "attachment;filename=relatorio_baterias.pdf"})

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

        # Gerar lista de baterias (endereços MAC e empresas) para a localização filtrada
        if data:
            batteries = sorted(set([(row[2], row[1]) for row in data]))  # (mac_address, company_name)
            batteries_loc = sorted(set([row[3] for row in data]))  # Lista única e ordenada de localizações
        
        # Gerar gráfico e alertas
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
