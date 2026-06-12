const fs = require('fs');

const path = 'c:/Users/geryb/Desktop/Gastos_OCR/frontend/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

const API_BASE = "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`";

content = content.replace(/'http:\/\/localhost:8000\/upload-receipt'/g, `${API_BASE} + '/upload-receipt'`);
content = content.replace(/`http:\/\/localhost:8000\/admin\/history\?email=\$\{encodeURIComponent\(user\.email\)\}`/g, "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/admin/history?email=${encodeURIComponent(user.email)}`");
content = content.replace(/`http:\/\/localhost:8000\/history\?email=\$\{encodeURIComponent\(user\.email\)\}`/g, "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/history?email=${encodeURIComponent(user.email)}`");
content = content.replace(/`http:\/\/localhost:8000\/expense\/\$\{id\}`/g, "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${id}`");
content = content.replace(/`http:\/\/localhost:8000\/expense\/\$\{editingExpense\.id\}`/g, "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${editingExpense.id}`");

fs.writeFileSync(path, content, 'utf8');
console.log('App.jsx URLs updated successfully.');
