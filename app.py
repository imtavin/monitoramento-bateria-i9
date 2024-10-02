from flask import Flask, render_template
import sqlite3
import plotly.graph_objs as go
from plotly.subplots import make_subplots

app = Flask(__name__)

# Função para pegar dados de cada tabela (tensão, resistência, temperatura)
def get_battery_data(query):
    conn = sqlite3.connect('bateria.db')
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    return data

# Função para criar gráficos interativos e estilizados com Plotly
def create_graphs():
    # Obter dados de cada tabela
    tensao_data = get_battery_data("SELECT data_hora, valor FROM tensao ORDER BY data_hora")
    resistencia_data = get_battery_data("SELECT data_hora, valor FROM resistencia ORDER BY data_hora")
    temperatura_data = get_battery_data("SELECT data_hora, valor FROM temperatura ORDER BY data_hora")
    
    # Separar dados (timestamps, valores)
    timestamps_tensao = [row[0] for row in tensao_data]
    tensao = [row[1] for row in tensao_data]

    timestamps_resistencia = [row[0] for row in resistencia_data]
    resistencia = [row[1] for row in resistencia_data]

    timestamps_temperatura = [row[0] for row in temperatura_data]
    temperatura = [row[1] for row in temperatura_data]

    # Criar subplots para os gráficos de tensão, resistência e temperatura
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=('Tensão (V)', 'Resistência (Ω)', 'Temperatura (°C)'))

    # Estilo de linha e cores personalizados
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

    # Gráfico de tensão
    fig.add_trace(go.Scatter(x=timestamps_tensao, y=tensao, mode='lines', name='Tensão',
                             line=dict(color=colors[0], width=2)), row=1, col=1)

    # Gráfico de resistência
    fig.add_trace(go.Scatter(x=timestamps_resistencia, y=resistencia, mode='lines', name='Resistência',
                             line=dict(color=colors[1], width=2)), row=2, col=1)

    # Gráfico de temperatura
    fig.add_trace(go.Scatter(x=timestamps_temperatura, y=temperatura, mode='lines', name='Temperatura',
                             line=dict(color=colors[2], width=2)), row=3, col=1)

    # Atualizar layout com mais estilo
    fig.update_layout(
        height=900,  # Altura dos gráficos
        title_text="Monitoramento da Saúde da Bateria",  # Título principal
        title_x=0.5,  # Centralizar o título
        showlegend=False,  # Ocultar legenda para simplificação
        plot_bgcolor='#f9f9f9',  # Fundo do gráfico
        paper_bgcolor='#f2f2f2',  # Fundo da área de visualização
        font=dict(family="Arial", size=14, color="#000000"),  # Fonte padrão
        margin=dict(l=40, r=40, t=80, b=40)  # Margens para dar mais espaçamento
    )

    # Configuração do eixo X compartilhado
    fig.update_xaxes(title_text="Tempo", showgrid=True, gridcolor='#e6e6e6', tickangle=45)
    fig.update_yaxes(showgrid=True, gridcolor='#e6e6e6')

    # Retornar gráfico em formato HTML
    return fig.to_html(full_html=False)

@app.route('/')
def index():
    # Gerar os gráficos e passar para o template
    graph = create_graphs()
    return render_template('dashboard.html', graph=graph)

if __name__ == '__main__':
    app.run(debug=True)
