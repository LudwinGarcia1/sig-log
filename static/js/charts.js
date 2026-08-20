const SIGLOG_COLORS = {
  primary:   "#00050c",   // barras principales (envíos, entregas)
  secondary: "#c0cac5",   // segunda serie (operadores)
  accent:    "#14fdde",   // el valor más alto de una serie
  average:   "#2792f0",   // línea de promedio
  danger:    "#302022",   // retrasos
  pie: ["#0d6efd", "#20c997", "#ffc107", "#6f42c1", "#fd7e14", "#dc3545"],
};

/* Promedio aritmético de una serie; 0 si viene vacía. */
function siglogAverage(values) {
  if (!values.length) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

/* Un color por barra, con la más alta resaltada en el color de acento. */
function siglogMaxColors(values, base, accent) {
  const peak = Math.max(...values);
  return values.map(value => (value === peak ? accent : base));
}

/* Dataset de línea horizontal constante que dibuja el promedio de la serie. */
function siglogAverageDataset(values, unit) {
  const average = siglogAverage(values);
  return {
    type: "line",
    label: `Promedio: ${average.toLocaleString("es-MX", {maximumFractionDigits: 1})}${unit || ""}`,
    data: values.map(() => average),
    borderColor: SIGLOG_COLORS.average,
    borderDash: [6, 4],
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
  };
}

/* Etiquetas con el porcentaje ya escrito, para gráficas de pastel. */
function siglogPercentLabels(labels, values) {
  const total = values.reduce((sum, value) => sum + value, 0) || 1;
  return labels.map(
    (label, index) => `${label} — ${(values[index] / total * 100).toFixed(1)}%`
  );
}

/* Tooltip que muestra el valor y su porcentaje del total. */
function siglogPercentTooltip(values) {
  const total = values.reduce((sum, value) => sum + value, 0) || 1;
  return {
    callbacks: {
      label: context => {
        const value = context.parsed;
        return ` ${value.toLocaleString("es-MX")} (${(value / total * 100).toFixed(1)}%)`;
      },
    },
  };
}

/* Marca el punto más alto de una serie en el subtítulo de la gráfica. */
function siglogPeakSubtitle(labels, values, noun) {
  const peak = Math.max(...values);
  const where = labels[values.indexOf(peak)];
  return {
    display: true,
    text: `Máximo: ${where} con ${peak.toLocaleString("es-MX")} ${noun || ""}`.trim(),
    color: SIGLOG_COLORS.accent,
    font: {weight: "bold"},
    padding: {bottom: 8},
  };
}
