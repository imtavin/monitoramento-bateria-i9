from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import plotly.graph_objs as go
from plotly.subplots import make_subplots

app = Flask(__name__)

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

        return redirect(url_for('index'))  # Redireciona para a página principal após o cadastro

    return render_template('cadastro_bateria.html')

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

    #print(temperatures)

    fig = make_subplots(rows=3, cols=1, subplot_titles=('Voltage (V)', 'Resistance (Ω)', 'Temperature (°C)'))

    # Adiciona os dados ao gráfico
    fig.add_trace(go.Scatter(x=timestamps, y=voltages, mode='lines', name='Voltage'), row=1, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=resistances, mode='lines', name='Resistance'), row=2, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=temperatures, mode='lines', name='Temperature'), row=3, col=1)

    # Ajustar o layout
    fig.update_layout(height=800, title_text="Battery Health for MAC", showlegend=False)

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
        #print(data)

        # Gerar lista de baterias (endereços MAC e empresas) para a localização filtrada
        if data:
            batteries = sorted(set([(row[2], row[1]) for row in data])) # (mac_address, company_name)
            batteries_loc = sorted(set([row[3] for row in data]))  # Lista única e ordenada de localizações
        
        # Gerar gráfico apenas para o MAC filtrado
        graph = create_graphs(data)

        return render_template('dashboard.html', graph=graph, batteries=batteries, batteries_loc=batteries_loc, filters=filters)
    
    # Se for um GET (sem filtro), carrega todos os dados
    data = get_battery_data()
    graph = create_graphs(data)
    
    return render_template('dashboard.html', graph=graph, batteries=batteries, batteries_loc=batteries_loc, filters=filters)


if __name__ == '__main__':
    app.run(debug=True)
