import math
import plotly.graph_objects as go

STATUS_COLOR = {
    "HEALTHY": "#22c55e", "WATCH": "#eab308",
    "WARNING": "#f97316", "CRITICAL": "#ef4444",
}

def _positions(n):
    # Generate a clean factory grid so newly added machines also appear.
    cols = 4
    positions = []
    for i in range(n):
        row, col = divmod(i, cols)
        positions.append((1.5 + col * 2.8, 2.0 + row * 2.8, 1.0))
    return positions

def factory_view(machines, selected=None):
    pos = _positions(len(machines))
    x, y, z = zip(*pos) if pos else ([], [], [])
    colors = [STATUS_COLOR.get(m["status"], "#64748b") for m in machines]
    sizes = [12 + m["risk"] / 7 + (7 if m["machine_id"] == selected else 0) for m in machines]
    custom = [[m["machine_id"], m["status"], m["risk"], m["rul_hours"], m["temp"], m["vibration"], m["pressure"]] for m in machines]
    fig = go.Figure(go.Scatter3d(
        x=x, y=y, z=z, mode="markers+text", text=[m["machine_id"] for m in machines], textposition="top center",
        customdata=custom,
        hovertemplate=("<b>%{customdata[0]}</b><br>Status: %{customdata[1]}<br>Risk: %{customdata[2]}%<br>"
                       "RUL: %{customdata[3]} hrs<br>Temp: %{customdata[4]}°C<br>Vibration: %{customdata[5]}<br>"
                       "Pressure: %{customdata[6]}<extra></extra>"),
        marker=dict(size=sizes, color=colors, opacity=.95, line=dict(width=2, color="#f8fafc")),
    ))
    # Connect machines within each production row.
    for row in range(math.ceil(len(pos) / 4)):
        pts = pos[row*4:(row+1)*4]
        if len(pts) > 1:
            fig.add_trace(go.Scatter3d(x=[p[0] for p in pts], y=[p[1] for p in pts], z=[0.7]*len(pts),
                                       mode="lines", line=dict(width=4, color="#475569"), hoverinfo="skip", showlegend=False))
    fig.update_layout(height=560, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(xaxis=dict(title="Production Line", showbackground=False, gridcolor="#334155"),
                   yaxis=dict(title="Factory Zone", showbackground=False, gridcolor="#334155"),
                   zaxis=dict(title="Level", showbackground=False, gridcolor="#334155"),
                   bgcolor="rgba(0,0,0,0)"), showlegend=False)
    return fig
