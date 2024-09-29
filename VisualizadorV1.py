from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_cytoscape as cyto
import base64
import io
import pandas as pd
import networkx as nx

app = Dash(__name__)

# Funções de BFS e DFS
def bfs_aula(G, s):
    c = {}
    d = {}
    pi = {}
    o = {}
    for u in G.nodes():
        c[u] = "Branco"
        d[u] = None
        pi[u] = None
    c[s] = "Cinza"
    d[s] = 0
    pi[s] = None  
    Q = [s]
    x = 1
    while Q:
        u = Q.pop(0)
        o[x] = u
        x = x + 1
        for v in G.adj[u]:
            if c[v] == "Branco":
                c[v] = "Cinza"
                d[v] = d[u] + 1
                pi[v] = u
                Q.append(v)
        c[u] = "Preto"
    return o, d, pi

def dfs_aula(G):
    c = {}
    pi = {}
    d = {}
    f = {}
    for u in G.nodes():
        c[u] = "Branco"
        pi[u] = None
        d[u] = None
        f[u] = None
    tempo = 0
    for u in G.nodes():
        if c[u] == "Branco":
            tempo = dfs_visit_aula(G, u, c, pi, d, f, tempo)
    return c, pi, d, f

def dfs_visit_aula(G, u, c, pi, d, f, tempo):
    tempo = tempo + 1
    d[u] = tempo
    c[u] = "Cinza"
    for v in G.adj[u]:
        if c[v] == "Branco":
            pi[v] = u
            tempo = dfs_visit_aula(G, v, c, pi, d, f, tempo)
    c[u] = "Preto"
    tempo = tempo + 1
    f[u] = tempo
    return tempo

# Layout do app
app.layout = html.Div(style={'backgroundColor': 'black', 'color': 'white', 'padding': '20px'}, children=[
    dcc.Upload(
        id='upload-data',
        children=html.Button('Carregar Arquivo', style={'margin': '5px'}),
        multiple=False
    ),
    dcc.Download(id='download-data'),

    html.Div(style={'display': 'flex', 'justify-content': 'center', 'margin-top': '10px'}, children=[
        html.Button('Salvar Grafo', id='save-button', style={'margin': '5px'}),
        html.Button('Adicionar Nó', id='add-node', style={'margin': '5px'}),
        html.Button('Remover Nó', id='remove-node', style={'margin': '5px'}),
        html.Button('Alternar Direcionado/Não Direcionado', id='toggle-directed', style={'margin': '5px'}),
        html.Button('Alternar Ponderado/Não Ponderado', id='toggle-weighted', style={'margin': '5px'}),
    ]),

    html.Div(id='graph-info', style={'textAlign': 'center', 'margin-top': '10px'}),
    html.Div(id='graph-info-detail', style={'textAlign': 'center'}),

    cyto.Cytoscape(
        id='cytoscape',
        layout={'name': 'preset', 'animate': True},
        style={'width': '100%', 'height': '400px', 'backgroundColor': 'black'},
        elements=[],
        panningEnabled=True,
        userZoomingEnabled=True,
        zoomingEnabled=True,
        minZoom=0.5,
        maxZoom=2,
        stylesheet=[
            {'selector': 'node', 'style': {'content': 'data(label)', 'text-valign': 'center', 'text-halign': 'center', 'background-color': 'white', 'color': 'black'}},
            {'selector': 'edge', 'style': {'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'line-color': 'white', 'target-arrow-color': 'white', 'label': 'data(weight)', 'color': 'white'}}
        ],
        tapNodeData={'selector': 'node'},
        tapEdgeData={'selector': 'edge'}
    ),

    html.Div(id='error-message'),

    html.Div(style={'textAlign': 'center', 'margin-top': '10px'}, children=[
        dcc.Input(id='edge-weight-input', type='number', placeholder='Digite o novo peso da aresta', style={'margin': '5px'}),
        html.Button('Atualizar Peso da Aresta', id='update-weight-button', n_clicks=0, style={'margin': '5px'})
    ]),

    html.Div(style={'textAlign': 'center', 'margin-top': '10px'}, children=[
        html.Button('Executar BFS', id='bfs-button', style={'margin': '5px'}),
        html.Button('Executar DFS', id='dfs-button', style={'margin': '5px'})
    ]),

    html.Div(id='bfs-output', style={'textAlign': 'center', 'margin-top': '10px'}),
    html.Div(id='dfs-output', style={'textAlign': 'center'})
])

# Inicializar o estado global
global_state = {
    'directed': True,  # Assumir que o tipo padrão de grafo é direcionado
    'weighted': False, # Assumir que o tipo padrão de grafo é não ponderado
    'selected_node_id': None,
    'current_weight': 1,  # Peso padrão para novas arestas
    'selected_edge_id': None  # Para armazenar o ID da aresta selecionada para atualizações de peso
}

@app.callback(
    [Output('cytoscape', 'elements'),
     Output('graph-info', 'children'),
     Output('graph-info-detail', 'children')],
    [Input('upload-data', 'contents'),
     Input('add-node', 'n_clicks'),
     Input('remove-node', 'n_clicks'),
     Input('toggle-directed', 'n_clicks'),
     Input('toggle-weighted', 'n_clicks'),
     Input('cytoscape', 'tapNodeData'),
     Input('cytoscape', 'tapEdgeData')],
    [State('cytoscape', 'elements'),
     State('upload-data', 'filename'),
     State('edge-weight-input', 'value'),
     State('update-weight-button', 'n_clicks')],
    prevent_initial_call=True
)
def update_graph(contents, add_node_clicks, remove_node_clicks, toggle_directed_clicks, toggle_weighted_clicks, node_data, edge_data, elements, filename, edge_weight, update_weight_button_clicks):
    global global_state

    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if elements is None:
        elements = []

    if triggered_id == 'upload-data':
        if contents is None:
            return elements, '', ''
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = io.StringIO(decoded.decode('utf-8'))
        df = pd.read_csv(data)

        # Verificar se as colunas 'x' e 'y' existem
        nodes = [{'data': {'id': row['id'], 'label': row['label']},
                  'position': {'x': row['x'] if 'x' in df.columns else 100, 'y': row['y'] if 'y' in df.columns else 100}}
                 for _, row in df[df['type'] == 'node'].iterrows()]
        edges = [{'data': {'source': row['source'], 'target': row['target'], 'weight': row.get('weight', global_state['current_weight'])}}
                 for _, row in df[df['type'] == 'edge'].iterrows()]
        elements = nodes + edges

    elif triggered_id == 'add-node':
        new_node_id = str(len([e for e in elements if 'data' in e and 'label' in e['data']]) + 1)
        new_node = {'data': {'id': new_node_id, 'label': f'Nó {new_node_id}'}, 'position': {'x': 100, 'y': 100}}
        elements.append(new_node)

    elif triggered_id == 'remove-node':
        nodes = [e for e in elements if 'data' in e and 'label' in e['data']]
        if nodes:
            elements = [e for e in elements if e['data']['id'] != nodes[-1]['data']['id']]

    elif triggered_id == 'toggle-directed':
        global_state['directed'] = not global_state['directed']

        updated_elements = []
        for element in elements:
            if 'data' in element:
                data = element['data']
                if 'source' in data and 'target' in data:
                    if global_state['directed']:
                        data['target-arrow-shape'] = 'triangle'
                    else:
                        data.pop('target-arrow-shape', None)
                updated_elements.append({'data': data, 'classes': element.get('classes', '')})
            else:
                updated_elements.append(element)
        
        elements = updated_elements

    elif triggered_id == 'toggle-weighted':
        global_state['weighted'] = not global_state['weighted']

        updated_elements = []
        for element in elements:
            if 'data' in element:
                data = element['data']
                if 'source' in data and 'target' in data:
                    if global_state['weighted']:
                        if 'weight' not in data:
                            data['weight'] = global_state['current_weight']
                    else:
                        data.pop('weight', None)
                updated_elements.append({'data': data, 'classes': element.get('classes', '')})
            else:
                updated_elements.append(element)
        
        elements = updated_elements

    elif triggered_id == 'cytoscape':
        if node_data:
            clicked_node_id = node_data['id']
            if global_state['selected_node_id'] is None:
                global_state['selected_node_id'] = clicked_node_id
            else:
                if global_state['selected_node_id'] != clicked_node_id:
                    new_edge = {'data': {'source': global_state['selected_node_id'], 'target': clicked_node_id}}
                    if global_state['weighted']:
                        new_edge['data']['weight'] = global_state['current_weight']
                    elements.append(new_edge)
                global_state['selected_node_id'] = None

    elif triggered_id == 'cytoscape.tapEdgeData':
        if edge_data:
            global_state['selected_edge_id'] = edge_data['id']

    # Atualizar peso da aresta se o botão for clicado
    if update_weight_button_clicks > 0:
        if global_state['selected_edge_id'] is not None and edge_weight is not None:
            try:
                new_weight = float(edge_weight)
                elements = [
                    {
                        'data': {
                            **element['data'],
                            'weight': new_weight if element['data'].get('id') == global_state['selected_edge_id'] and 'source' in element['data'] and 'target' in element['data'] else element['data'].get('weight')
                        }
                    } if 'data' in element and 'source' in element['data'] and 'target' in element['data'] else element
                    for element in elements
                ]
                global_state['selected_edge_id'] = None  # Resetar ID da aresta selecionada
            except ValueError:
                pass

    # Atualizar informações do grafo
    nodes = [e['data'] for e in elements if 'data' in e and 'label' in e['data']]
    edges = [e['data'] for e in elements if 'data' in e and 'source' in e['data']]
    
    num_nodes = len(nodes)
    num_edges = len(edges)
    info = f"Número de nós: {num_nodes}, Número de arestas: {num_edges}"
    
    graph_type = "Dirigido" if global_state['directed'] else "Não Dirigido"
    weight_type = "Ponderado" if global_state['weighted'] else "Não Ponderado"
    detail_info = f"Tipo de Grafo: {graph_type}, Tipo de Peso: {weight_type}"

    return elements, info, detail_info

@app.callback(
    Output('cytoscape', 'stylesheet'),
    [Input('toggle-directed', 'n_clicks'),
     Input('toggle-weighted', 'n_clicks')],
    prevent_initial_call=True
)
def update_stylesheet(*args):
    # Determinar stylesheet baseado na direção e ponderação atuais
    stylesheet = [
        {'selector': 'node', 'style': {'content': 'data(label)', 'text-valign': 'center', 'text-halign': 'center', 'background-color': 'white', 'color': 'black'}},
        {'selector': 'edge', 'style': {'curve-style': 'bezier',
                                        'target-arrow-shape': 'triangle' if global_state['directed'] else 'none',
                                        'line-color': 'white',
                                        'target-arrow-color': 'white',
                                        'label': 'data(weight)' if global_state['weighted'] else 'none',
                                        'color': 'white'}}
    ]
    return stylesheet

@app.callback(
    Output('download-data', 'data'),
    Input('save-button', 'n_clicks'),
    State('cytoscape', 'elements')
)
def save_graph(n_clicks, elements):
    if n_clicks is None:
        return None

    nodes = [e['data'] for e in elements if 'data' in e and 'label' in e['data']]
    edges = [e['data'] for e in elements if 'data' in e and 'source' in e['data']]

    df_nodes = pd.DataFrame(nodes)
    df_edges = pd.DataFrame(edges)
    df_nodes['type'] = 'node'
    df_edges['type'] = 'edge'
    df = pd.concat([df_nodes, df_edges], ignore_index=True)

    return dcc.send_data_frame(df.to_csv, 'dados_grafo.csv')

@app.callback(
    [Output('bfs-output', 'children'),
     Output('dfs-output', 'children')],
    [Input('bfs-button', 'n_clicks'),
     Input('dfs-button', 'n_clicks')],
    State('cytoscape', 'elements')
)
def perform_searches(bfs_clicks, dfs_clicks, elements):
    if elements is None:
        return '', ''
    
    # Criar o grafo a partir dos elementos
    G = nx.DiGraph() if global_state['directed'] else nx.Graph()
    for element in elements:
        if 'data' in element:
            data = element['data']
            if 'source' in data and 'target' in data:
                G.add_edge(data['source'], data['target'], weight=data.get('weight', 1))
            elif 'id' in data and 'label' in data:
                G.add_node(data['id'])
    
    bfs_output = ''
    dfs_output = ''
    
    if bfs_clicks:
        # Executar BFS
        if len(G.nodes()) > 0:
            start_node = next(iter(G.nodes()))
            o, d, pi = bfs_aula(G, start_node)
            bfs_output = f"BFS ordem: {o}, BFS distâncias: {d}, BFS predecessores: {pi}"
        else:
            bfs_output = "O grafo está vazio."

    if dfs_clicks:
        # Executar DFS
        if len(G.nodes()) > 0:
            c, pi, d, f = dfs_aula(G)
            dfs_output = f"DFS cores: {c}, DFS predecessores: {pi}, DFS tempos de descoberta: {d}, DFS tempos de finalização: {f}"
        else:
            dfs_output = "O grafo está vazio."

    return bfs_output, dfs_output

if __name__ == '__main__':
    app.run_server(debug=True)
