// LeadDashboard.jsx (CDN globals version)
// React + Tailwind dashboard for Lead Quality Scorer & Prioritizer

const { useState } = React;

function LeadDashboard() {
  const [file, setFile] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ minScore: 0 });

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLoading(true);
    try {
      const res = await axios.post('http://localhost:8001/score', formData);
      setLeads(res.data);
    } catch (err) {
      console.error(err);
      alert('Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const topLeads = leads.filter(l => l.score >= filters.minScore);
    const csvContent = [
      Object.keys(topLeads[0] || {}).join(','),
      ...topLeads.map(l => Object.values(l).join(','))
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'prioritized.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredLeads = leads.filter(l => l.score >= filters.minScore);

  return (
    React.createElement('div', { className: 'p-6 max-w-6xl mx-auto' },
      React.createElement('h1', { className: 'text-2xl font-bold mb-4' }, 'Lead Quality Dashboard'),
      React.createElement('div', { className: 'flex space-x-4 mb-4' },
        React.createElement('input', { type: 'file', onChange: handleFileChange, className: 'border p-2' }),
        React.createElement('button', { onClick: handleUpload, className: 'bg-blue-500 text-white px-4 py-2 rounded' }, 'Upload & Score'),
        React.createElement('button', { onClick: handleDownload, className: 'bg-green-500 text-white px-4 py-2 rounded' }, 'Download Top Leads'),
        React.createElement('input', {
          type: 'number', min: '0', max: '100', value: filters.minScore,
          onChange: e => setFilters({ ...filters, minScore: Number(e.target.value) }),
          className: 'border p-2 w-24', placeholder: 'Min Score'
        })
      ),
      loading && React.createElement('p', null, 'Processing leads...'),
      (filteredLeads.length > 0) && (
        React.createElement('table', { className: 'w-full border-collapse border border-gray-200' },
          React.createElement('thead', { className: 'bg-gray-100' },
            React.createElement('tr', null,
              React.createElement('th', { className: 'border p-2' }, 'Name'),
              React.createElement('th', { className: 'border p-2' }, 'Email'),
              React.createElement('th', { className: 'border p-2' }, 'Company'),
              React.createElement('th', { className: 'border p-2' }, 'Job Title'),
              React.createElement('th', { className: 'border p-2' }, 'Score'),
              React.createElement('th', { className: 'border p-2' }, 'Status')
            )
          ),
          React.createElement('tbody', null,
            filteredLeads.map((lead, idx) => (
              React.createElement('tr', { key: idx, className: 'hover:bg-gray-50' },
                React.createElement('td', { className: 'border p-2' }, lead.full_name || `${lead.first_name} ${lead.last_name}`),
                React.createElement('td', { className: 'border p-2' }, lead.email),
                React.createElement('td', { className: 'border p-2' }, lead.company_name),
                React.createElement('td', { className: 'border p-2' }, lead.job_title),
                React.createElement('td', { className: `border p-2 font-bold ${lead.score >= 75 ? 'text-green-600' : lead.score >= 50 ? 'text-yellow-600' : 'text-red-600'}` }, lead.score),
                React.createElement('td', { className: 'border p-2' }, lead.score >= 50 ? '✅ Ready' : '⚠️ Low')
              )
            ))
          )
        )
      ),
      (filteredLeads.length === 0 && !loading) && React.createElement('p', null, 'No leads to display. Upload a CSV to start.')
    )
  );
}

function mountApp() {
  const root = document.getElementById('root');
  ReactDOM.createRoot(root).render(React.createElement(LeadDashboard));
}

window.mountLeadDashboard = mountApp;
