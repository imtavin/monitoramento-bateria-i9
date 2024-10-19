from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import plotly.graph_objs as go
from plotly.subplots import make_subplots

app = Flask(__name__)

# Função para conexão ao banco de dados
def connect_db():
    conn = sqlite3.connect('bateria.db')
    return conn

# Função para obter os dados da bateria
def get_battery_data(filters=None):
    conn = connect_db()
    cursor = conn.cursor()
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

        if 'start_date' in filters and 'end_date' in filters:
            query += " AND timestamp BETWEEN ? AND ?"
            params.append(filters['start_date'])
            params.append(filters['end_date'])

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
    # Organiza os dados por MAC Address
    mac_addresses = list(set(row[2] for row in data))  # Assume que o MAC está na coluna 2
    fig = make_subplots(rows=len(mac_addresses), cols=1, subplot_titles=[f"MAC: {mac}" for mac in mac_addresses])

    for i, mac in enumerate(mac_addresses):
        filtered_data = [row for row in data if row[2] == mac]  # Filtra dados por MAC
        timestamps = [row[6] for row in filtered_data]  # Timestamp
        voltages = [row[4] for row in filtered_data]    # Voltage

        fig.add_trace(go.Scatter(x=timestamps, y=voltages, mode='lines', name=f'Voltage (V) - {mac}'), row=i+1, col=1)

    fig.update_layout(height=300*len(mac_addresses), title_text="Battery Health by MAC", showlegend=False)

    return fig.to_html(full_html=False)
# Rota para a página inicial com filtros
@app.route('/', methods=['GET', 'POST'])
def index():
    filters = {}

    if request.method == 'POST':
        if request.form.get('location_filter'):
            filters['location'] = request.form['location_filter']
        if request.form.get('voltage_filter'):
            filters['voltage'] = request.form['voltage_filter']
        if request.form.get('mac_filter'):
            filters['mac_address'] = request.form['mac_filter']
        if request.form.get('start_date') and request.form.get('end_date'):
            filters['start_date'] = request.form['start_date']
            filters['end_date'] = request.form['end_date']

    data = get_battery_data(filters)
    graph = create_graphs(data)
    return render_template('dashboard.html', graph=graph)

if __name__ == '__main__':
    app.run(debug=True)
