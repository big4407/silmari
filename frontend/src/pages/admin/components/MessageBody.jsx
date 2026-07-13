export function ReportRow({ report }) {
  return (
    <tr>
      <td>{report.sn}</td>
      <td>{new Date(report.crt_dt).toLocaleString()}</td>
      <td>{report.rcptn_rgn_nm}</td>
      <td>{report.msg_cn}</td>
    </tr>
  );
}