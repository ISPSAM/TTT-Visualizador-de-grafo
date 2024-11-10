from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_cytoscape as cyto
import base64
import io
import pandas as pd
import networkx as nx

app = Dash(__name__)


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


def color_graph(G):
    color_palette = ['#FF0000', '#0000FF', '#00FF00', '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080']
    color_map = {}
   
    for node in G.nodes():
        
        neighbor_colors = {color_map[neighbor] for neighbor in G.neighbors(node) if neighbor in color_map}
        
        for color in color_palette:
            if color not in neighbor_colors:
                color_map[node] = color
                break
    
    return color_map


app.layout = html.Div(style={'backgroundColor': 'black', 'color': 'white', 'padding': '20px'}, children=[
    dcc.Upload(id='upload-data', children=html.Button('Carregar Arquivo', style={'margin': '5px'}), multiple=False),
    dcc.Download(id='download-data'),
    html.Div(style={'display': 'flex', 'justify-content': 'center', 'margin-top': '10px'}, children=[
        html.Button('Salvar Grafo', id='save-button', style={'margin': '5px'}),
        html.Button('Adicionar Nó', id='add-node', style={'margin': '5px'}),
        html.Button('Remover Nó', id='remove-node', style={'margin': '5px'}),
        html.Button('Alternar Direcionado/Não Direcionado', id='toggle-directed', style={'margin': '5px'}),
        html.Button('Alternar Ponderado/Não Ponderado', id='toggle-weighted', style={'margin': '5px'}),
        html.Button('Colorir Grafo', id='color-graph', style={'margin': '5px'}),
    ]),
    html.Div(id='graph-info', style={'textAlign': 'center', 'margin-top': '10px'}),
    html.Div(id='graph-info-detail', style={'textAlign': 'center'}),
    cyto.Cytoscape(
        id='cytoscape', layout={'name': 'preset', 'animate': True},
        style={'width': '100%', 'height': '400px', 'backgroundColor': 'black'},
        elements=[], panningEnabled=True, userZoomingEnabled=True, zoomingEnabled=True,
        minZoom=0.5, maxZoom=2, stylesheet=[
            {'selector': 'node', 'style': {'content': 'data(label)', 'text-valign': 'center', 'text-halign': 'center', 'background-color': 'data(color)', 'color': 'black'}},
            {'selector': 'edge', 'style': {'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'line-color': 'white', 'target-arrow-color': 'white', 'label': 'data(weight)', 'color': 'white'}}
        ]
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
    'directed': True,
    'weighted': False,
    'selected_node_id': None,
    'current_weight': 1,
    'selected_edge_id': None,
    'selected_nodes': [] 
}

@app.callback(
    [Output('cytoscape', 'elements'),
     Output('graph-info', 'children'),
     Output('graph-info-detail', 'children'),
     Output('bfs-output', 'children'),
     Output('dfs-output', 'children')],
    [Input('upload-data', 'contents'),
     Input('add-node', 'n_clicks'),
     Input('remove-node', 'n_clicks'),
     Input('toggle-directed', 'n_clicks'),
     Input('toggle-weighted', 'n_clicks'),
     Input('color-graph', 'n_clicks'),
     Input('bfs-button', 'n_clicks'),
     Input('dfs-button', 'n_clicks'),
     Input('cytoscape', 'tapNodeData')],  # Input para capturar os nós clicados
    [State('cytoscape', 'elements'),
     State('upload-data', 'filename'),
     State('edge-weight-input', 'value'),
     State('cytoscape', 'tapEdgeData')],
    prevent_initial_call=True
)
def update_graph(contents, add_node_clicks, remove_node_clicks, toggle_directed_clicks, toggle_weighted_clicks, color_graph_clicks, bfs_clicks, dfs_clicks,
                 node_data, elements, filename, edge_weight, edge_data):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

 
    if elements is None:
        elements = []
    graph_info = ''
    graph_info_detail = ''
    bfs_output = ''
    dfs_output = ''

  
    if triggered_id == 'upload-data' and contents:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = io.StringIO(decoded.decode('utf-8'))
        df = pd.read_csv(data)
        nodes = [{'data': {'id': row['id'], 'label': row['label']}, 'position': {'x': row['x'] if 'x' in df.columns else 100, 'y': row['y'] if 'y' in df.columns else 100}}
                 for _, row in df[df['type'] == 'node'].iterrows()]
        edges = [{'data': {'source': row['source'], 'target': row['target'], 'weight': row.get('weight', global_state['current_weight'])}}
                 for _, row in df[df['type'] == 'edge'].iterrows()]
        elements = nodes + edges


    if triggered_id == 'add-node':
        new_node_id = str(len([elem for elem in elements if 'data' in elem and 'id' in elem['data']]))
        new_node = {'data': {'id': new_node_id, 'label': f'Node {new_node_id}'}}
        elements.append(new_node)

    if triggered_id == 'remove-node' and node_data:
        node_to_remove = node_data['id']
        elements = [elem for elem in elements if not (elem.get('data', {}).get('id') == node_to_remove)]

   
    if triggered_id == 'toggle-directed':
        global_state['directed'] = not global_state['directed']

  
    if triggered_id == 'toggle-weighted':
        global_state['weighted'] = not global_state['weighted']

    # Colorir o grafo
    if triggered_id == 'color-graph':
        G = nx.Graph()
        for elem in elements:
            if 'data' in elem:
                if 'source' in elem['data'] and 'target' in elem['data']:
                    G.add_edge(elem['data']['source'], elem['data']['target'], weight=elem['data'].get('weight', 1))
                elif 'id' in elem['data']:
                    G.add_node(elem['data']['id'])
        color_map = color_graph(G)
        for elem in elements:
            if 'data' in elem and 'id' in elem['data']:
                node_id = elem['data']['id']
                color = color_map.get(node_id, '#FFFFFF')  
                elem['data']['color'] = color  
        graph_info = 'Grafo colorido com sucesso!'

    # Adicionar aresta
    if triggered_id == 'cytoscape' and node_data:
        if len(global_state['selected_nodes']) == 1:
           
            source = global_state['selected_nodes'][0]
            target = node_data['id']
            weight = edge_weight if edge_weight else global_state['current_weight']
            edge = {'data': {'source': source, 'target': target, 'weight': weight}}
            elements.append(edge)
            global_state['selected_nodes'] = []  
        else:
        
            global_state['selected_nodes'].append(node_data['id'])

    # Executar BFS
    if triggered_id == 'bfs-button' and node_data:
        start_node = node_data['id']
        G = nx.Graph()
        for elem in elements:
            if 'data' in elem:
                if 'source' in elem['data'] and 'target' in elem['data']:
                    G.add_edge(elem['data']['source'], elem['data']['target'], weight=elem['data'].get('weight', 1))
                elif 'id' in elem['data']:
                    G.add_node(elem['data']['id'])
        bfs_output = bfs_aula(G, start_node)

    # Executar DFS
    if triggered_id == 'dfs-button':
        G = nx.Graph()
        for elem in elements:
            if 'data' in elem:
                if 'source' in elem['data'] and 'target' in elem['data']:
                    G.add_edge(elem['data']['source'], elem['data']['target'], weight=elem['data'].get('weight', 1))
                elif 'id' in elem['data']:
                    G.add_node(elem['data']['id'])
        dfs_output = dfs_aula(G)

    return elements, graph_info, graph_info_detail, bfs_output, dfs_output

if __name__ == '__main__':
    app.run_server(debug=True)
