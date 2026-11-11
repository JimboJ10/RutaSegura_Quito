const periods = [
  { label: '2024', quito: 249, pilot: 9 },
  { label: '2025', quito: 271, pilot: 18 },
  { label: 'Enero–septiembre 2026', quito: 175, pilot: 5 },
];
const maximum = Math.max(...periods.flatMap(row => [row.quito, row.pilot]));

function Count({ value }: { value: number }) {
  return <td>{value}<span className="stat-track" aria-hidden="true">
    <span style={{ width: `${100 * value / maximum}%` }} />
  </span></td>;
}

export function HistoricalSafetyStats() {
  return <section className="safety-stats" aria-labelledby="safety-stats-title">
    <h3 id="safety-stats-title">Estadísticas históricas de seguridad</h3>
    <table>
      <caption>Homicidios intencionales registrados</caption>
      <thead><tr><th scope="col">Periodo</th><th scope="col">Cantón Quito</th><th scope="col">Zona piloto</th></tr></thead>
      <tbody>{periods.map(row => <tr key={row.label}>
        <th scope="row">{row.label}</th><Count value={row.quito} /><Count value={row.pilot} />
      </tr>)}</tbody>
      <tfoot><tr><th scope="row">Total</th>
        <td>{periods.reduce((sum, row) => sum + row.quito, 0)}</td>
        <td>{periods.reduce((sum, row) => sum + row.pilot, 0)}</td>
      </tr></tfoot>
    </table>
    <p>Fuente: Ministerio del Interior. En 2026 solo se incluyen registros de enero a septiembre.</p>
    <p>Estos registros históricos no representan peligros actuales ni predicciones de delitos.</p>
  </section>;
}
