import React, { useState, useEffect, useMemo } from 'react';
import { Camera, Upload, CheckCircle, FileText, RefreshCcw, DollarSign, Calendar, Hash, User, ShieldAlert, History, Filter, Edit2, Trash2, X, PieChart, Users, Building2, BarChart3, ArrowRight } from 'lucide-react';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import axios from 'axios';

const clientId = '478414532725-9plr5a15q3s6ti4qhref9m0as3baq6k3.apps.googleusercontent.com';
const ADMIN_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl"];

function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('scanner'); // 'scanner' | 'history' | 'admin'
  
  // Scanner States
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [costCenter, setCostCenter] = useState("");
  const [department, setDepartment] = useState("");

  // History & Admin States
  const [expenses, setExpenses] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [filterDept, setFilterDept] = useState("");
  const [filterCostCenter, setFilterCostCenter] = useState("");
  const [filterUser, setFilterUser] = useState("");
  
  // Edit States
  const [editingExpense, setEditingExpense] = useState(null);
  const [editForm, setEditForm] = useState({});

  const isAdmin = user && ADMIN_EMAILS.includes(user.email);

  const handleLoginSuccess = (credentialResponse) => {
    const decoded = jwtDecode(credentialResponse.credential);
    setUser({ name: decoded.name, email: decoded.email, picture: decoded.picture });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !user) return;
    if (!department) {
      setError("Por favor selecciona un Departamento antes de enviar.");
      return;
    }
    if (!costCenter) {
      setError("Por favor ingresa un Centro de Costo antes de enviar.");
      return;
    }
    
    setIsProcessing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('userName', user.name);
    formData.append('userEmail', user.email);
    formData.append('department', department);
    formData.append('costCenter', costCenter);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}` + '/upload-receipt', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        setResult(response.data.data);
      } else {
        setError("Error procesando la boleta: " + response.data.error);
      }
    } catch (err) {
      setError("Error de conexión con el servidor: " + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setResult(null);
    setError(null);
  };

  const fetchHistory = async () => {
    if (!user) return;
    setLoadingHistory(true);
    try {
      const endpoint = activeTab === 'admin' 
        ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/admin/history?email=${encodeURIComponent(user.email)}`
        : `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/history?email=${encodeURIComponent(user.email)}`;
        
      const response = await axios.get(endpoint);
      if (response.data.success) {
        setExpenses(response.data.data);
      } else {
        console.error("Error backend:", response.data.error);
      }
    } catch (err) {
      console.error("Error fetching history", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if ((activeTab === 'history' || activeTab === 'admin') && user) {
      fetchHistory();
    }
  }, [activeTab, user]);

  const handleDelete = async (id) => {
    if (window.confirm("¿Estás seguro de que quieres eliminar este gasto?")) {
      try {
        await axios.delete(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${id}`);
        fetchHistory();
      } catch (err) {
        console.error("Error deleting", err);
      }
    }
  };

  const startEdit = (exp) => {
    setEditingExpense(exp);
    setEditForm({
      departamento: exp.departamento,
      centro_costo: exp.centro_costo,
      rut_proveedor: exp.rut_proveedor,
      fecha_boleta: exp.fecha_boleta,
      monto_total: exp.monto_total
    });
  };

  const handleEditSubmit = async () => {
    try {
      await axios.put(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${editingExpense.id}`, editForm);
      setEditingExpense(null);
      fetchHistory();
    } catch (err) {
      console.error("Error updating", err);
      alert("Error al actualizar el gasto");
    }
  };

  const uniqueCostCenters = [...new Set(expenses.map(exp => exp.centro_costo))].filter(Boolean).sort();
  const uniqueUsers = [...new Set(expenses.map(exp => exp.usuario_nombre))].filter(Boolean).sort();

  const filteredExpenses = expenses.filter(exp => {
    const matchDept = filterDept ? exp.departamento === filterDept : true;
    const matchCC = filterCostCenter ? exp.centro_costo === filterCostCenter : true;
    const matchUser = filterUser ? exp.usuario_nombre === filterUser : true;
    return matchDept && matchCC && matchUser;
  });

  // KPIs
  const totalSpent = filteredExpenses.reduce((acc, exp) => acc + (parseFloat(exp.monto_total) || 0), 0);
  const totalInvoices = filteredExpenses.length;

  const expensesByDept = useMemo(() => {
    const res = {};
    filteredExpenses.forEach(exp => {
      res[exp.departamento] = (res[exp.departamento] || 0) + (parseFloat(exp.monto_total) || 0);
    });
    return Object.entries(res).sort((a,b) => b[1] - a[1]);
  }, [filteredExpenses]);

  const expensesByUser = useMemo(() => {
    const res = {};
    filteredExpenses.forEach(exp => {
      res[exp.usuario_nombre] = (res[exp.usuario_nombre] || 0) + (parseFloat(exp.monto_total) || 0);
    });
    return Object.entries(res).sort((a,b) => b[1] - a[1]);
  }, [filteredExpenses]);

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <div className="min-h-screen relative">
        
        {/* HEADER */}
        <header className="bg-white border-b border-slate-100 sticky top-0 z-20">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            
            {/* Left: App Branding (DealFlow Style) */}
            <div className="flex items-center gap-3">
              {/* Yellow DealFlow Icon */}
              <div className="shrink-0 h-10 w-10 bg-amber-500 rounded-[10px] flex items-center justify-center text-white shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
              </div>
              
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h1 className="text-[17px] font-bold text-[#1e293b] tracking-tight leading-none">DealFlow Gastos</h1>
                  <span className="bg-[#f1f5f9] text-[#64748b] text-[10px] font-bold px-1.5 py-0.5 rounded leading-none">v1.0</span>
                </div>
                <p className="text-[10px] uppercase tracking-widest text-[#94a3b8] font-bold mt-1 leading-none">Plataforma de Rendiciones</p>
              </div>
            </div>

            {/* Right: Company Logo Pill & User Profile */}
            <div className="flex items-center gap-5 shrink-0">
              
              {/* Powered by Pill */}
              <div className="flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                <img src="/logo.png" alt="E-Voltage" className="object-contain shrink-0 h-6" />
                <span className="text-[11px] text-slate-400 font-medium border-l border-slate-200 pl-3">Powered by DealFlow</span>
              </div>
              
              {user && (
                <div className="flex items-center gap-3">
                  <div className="hidden sm:block text-right">
                    {isAdmin && <p className="text-[9px] text-sky-500 font-bold uppercase tracking-widest leading-none mb-1">Administrador</p>}
                    <p className="text-sm font-bold text-slate-700 leading-none">{user.name}</p>
                  </div>
                  {user.picture ? (
                    <img src={user.picture} alt="Profile" className="h-8 w-8 rounded-full border border-slate-200 shadow-sm" />
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          
          {/* TABS */}
          {user && (
            <div className="max-w-7xl mx-auto px-4 flex gap-3 mt-4 mb-2 overflow-x-auto">
              <button 
                onClick={() => {setActiveTab('scanner'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                className={`px-4 py-2 rounded-lg font-medium text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'scanner' ? 'bg-indigo-50 text-indigo-600 shadow-sm border border-indigo-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
              >
                <div className="flex items-center gap-2">
                  <Camera className="h-4 w-4" /> Escanear Boleta
                </div>
              </button>
              <button 
                onClick={() => {setActiveTab('history'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                className={`px-4 py-2 rounded-lg font-medium text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'history' ? 'bg-purple-50 text-purple-600 shadow-sm border border-purple-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
              >
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4" /> Mi Historial
                </div>
              </button>
              {isAdmin && (
                <button 
                  onClick={() => {setActiveTab('admin'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                  className={`px-4 py-2 rounded-lg font-medium text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'admin' ? 'bg-sky-50 text-sky-600 shadow-sm border border-sky-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
                >
                  <div className="flex items-center gap-2">
                    <PieChart className="h-4 w-4" /> Panel Administrador
                  </div>
                </button>
              )}
            </div>
          )}
        </header>

        <main className="max-w-6xl mx-auto px-4 py-8">
          {!user ? (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 flex flex-col items-center text-center max-w-md mx-auto mt-16 bg-white">
              <div className="h-20 w-20 bg-sky-50 rounded-full flex items-center justify-center mb-6 border border-sky-100">
                <ShieldAlert className="h-10 w-10 text-[#38bdf8]" />
              </div>
              <h2 className="text-3xl font-bold text-slate-800 mb-3">Acceso Restringido</h2>
              <p className="text-slate-500 mb-8 leading-relaxed">Inicia sesión con tu cuenta corporativa para gestionar y rendir gastos.</p>
              <div className="transform hover:scale-105 transition-transform duration-300">
                <GoogleLogin
                  onSuccess={handleLoginSuccess}
                  onError={() => console.log('Login Failed')}
                  theme="outline"
                  shape="pill"
                />
              </div>
            </div>
          ) : activeTab === 'scanner' ? (
            /* TAB SCANNER */
            !result ? (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-lg mx-auto bg-white">
                <div className="p-8">
                  <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">Ingresar Nuevo Gasto</h2>
                    <p className="text-slate-500 text-sm">Nuestra IA extraerá los datos automáticamente.</p>
                  </div>
                  
                  <div className="w-full mb-5">
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Departamento</label>
                    <select 
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3.5 rounded-xl text-sm"
                    >
                      <option value="">-- Selecciona el Departamento --</option>
                      <option value="Ventas">Ventas</option>
                      <option value="Gerencia">Gerencia</option>
                      <option value="Operaciones">Operaciones</option>
                      <option value="Administración">Administración</option>
                    </select>
                  </div>

                  <div className="w-full mb-8">
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Centro de Costo</label>
                    <input 
                      type="text"
                      value={costCenter}
                      onChange={(e) => setCostCenter(e.target.value.toUpperCase())}
                      placeholder="Ej: OEV-EXT-260008"
                      className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3.5 rounded-xl text-sm font-mono uppercase"
                    />
                  </div>

                  <label className={`upload-area w-full h-56 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center cursor-pointer transition-all ${file ? 'border-[#38bdf8] bg-sky-50' : 'border-slate-300 hover:bg-slate-50'} ${isProcessing ? 'pulse-animation' : ''}`}>
                    {file ? (
                      <>
                        <CheckCircle className="h-12 w-12 text-[#38bdf8] mb-3" />
                        <span className="text-sm font-medium text-slate-700">{file.name}</span>
                        <span className="text-xs text-slate-400 mt-1">Archivo seleccionado</span>
                      </>
                    ) : (
                      <>
                        <div className="h-16 w-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                          <Camera className="h-8 w-8 text-slate-400" />
                        </div>
                        <span className="text-sm font-medium text-slate-500">Toca para abrir cámara o galería</span>
                      </>
                    )}
                    <input 
                      type="file" 
                      accept="image/*" 
                      capture="environment" 
                      className="hidden" 
                      onChange={handleFileChange}
                    />
                  </label>

                  <button 
                    onClick={handleUpload}
                    disabled={!file || isProcessing}
                    className={`mt-8 w-full py-4 rounded-xl font-bold flex items-center justify-center gap-3 text-lg ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors shadow-sm font-bold tracking-wide'}`}
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCcw className="h-6 w-6 animate-spin" /> Procesando...
                      </>
                    ) : (
                      <>
                        <Upload className="h-6 w-6" /> Enviar y Analizar
                      </>
                    )}
                  </button>
                  {error && (
                    <div className="mt-5 w-full p-4 bg-red-50 border border-red-200 text-red-600 text-sm rounded-xl text-center font-medium flex items-center justify-center gap-2">
                      <ShieldAlert className="h-4 w-4" /> {error}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-lg mx-auto bg-white">
                <div className="bg-gradient-to-br from-[#38bdf8] to-[#0284c7] p-8 flex flex-col items-center text-white relative overflow-hidden">
                  <div className="absolute -right-10 -top-10 opacity-20">
                    <CheckCircle className="h-48 w-48" />
                  </div>
                  <CheckCircle className="h-16 w-16 mb-4 relative z-10" />
                  <h2 className="text-3xl font-bold mb-2 relative z-10">¡Éxito!</h2>
                  <p className="text-sky-100 font-medium relative z-10 text-center">Gasto registrado en el CRM y Finanzas.</p>
                </div>
                
                <div className="p-8">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 border-b border-slate-100 pb-2">Datos Extraídos por IA</h3>
                  
                  <div className="space-y-3">
                    <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="h-10 w-10 rounded-lg bg-white shadow-sm flex items-center justify-center">
                        <Hash className="h-5 w-5 text-slate-400" />
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">RUT Proveedor</p>
                        <p className="text-sm font-semibold text-slate-800">{result.rut_proveedor}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="h-10 w-10 rounded-lg bg-white shadow-sm flex items-center justify-center">
                        <Calendar className="h-5 w-5 text-slate-400" />
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Fecha Emisión</p>
                        <p className="text-sm font-semibold text-slate-800">{result.fecha}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 p-5 bg-sky-50 rounded-xl border border-sky-100">
                      <div className="h-12 w-12 rounded-lg bg-white shadow-sm flex items-center justify-center">
                        <DollarSign className="h-6 w-6 text-[#38bdf8]" />
                      </div>
                      <div>
                        <p className="text-[10px] text-sky-600 font-bold uppercase tracking-wider">Monto Total</p>
                        <p className="text-3xl font-bold text-[#0284c7]">${result.monto_total?.toLocaleString('es-CL')}</p>
                      </div>
                    </div>
                  </div>

                  <button 
                    onClick={resetForm}
                    className="mt-8 w-full py-4 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded-xl font-bold transition-all flex items-center justify-center gap-2 border border-slate-200"
                  >
                    Registrar otro gasto <ArrowRight className="h-4 w-4 text-slate-400" />
                  </button>
                </div>
              </div>
            )
          ) : (
            /* TAB HISTORY OR ADMIN CRM */
            <div className="space-y-6">
              
              {/* Dashboard Stats */}
              {activeTab === 'admin' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white p-6 col-span-1 md:col-span-2 relative overflow-hidden group">
                    <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
                      <DollarSign className="h-40 w-40 text-[#38bdf8]" />
                    </div>
                    <div className="flex items-center gap-4 mb-4 relative z-10">
                      <div className="h-12 w-12 bg-sky-50 border border-sky-100 text-[#38bdf8] rounded-xl flex items-center justify-center shadow-sm">
                        <DollarSign className="h-6 w-6" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Inversión Global</p>
                        <p className="text-slate-500 text-xs">Total Empresa</p>
                      </div>
                    </div>
                    <p className="text-5xl font-black text-slate-800 relative z-10 tracking-tight">${totalSpent.toLocaleString('es-CL')}</p>
                    <p className="text-sm text-sky-600 mt-3 font-medium relative z-10 flex items-center gap-2">
                      <FileText className="h-4 w-4" /> {totalInvoices} boletas procesadas
                    </p>
                  </div>

                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white p-6 flex flex-col justify-between">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="h-8 w-8 bg-slate-100 rounded-lg flex items-center justify-center"><Building2 className="h-4 w-4 text-slate-500" /></div>
                      <h3 className="font-bold text-slate-700 text-sm">Por Departamento</h3>
                    </div>
                    <div className="space-y-4">
                      {expensesByDept.slice(0,3).map(([dept, amount]) => (
                        <div key={dept}>
                          <div className="flex justify-between text-xs mb-1.5">
                            <span className="font-medium text-slate-500">{dept}</span>
                            <span className="font-bold text-slate-800">${amount.toLocaleString('es-CL')}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-[#38bdf8] h-1.5 rounded-full" style={{width: `${Math.max(5, (amount/totalSpent)*100)}%`}}></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white p-6 flex flex-col justify-between">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="h-8 w-8 bg-slate-100 rounded-lg flex items-center justify-center"><Users className="h-4 w-4 text-slate-500" /></div>
                      <h3 className="font-bold text-slate-700 text-sm">Top Usuarios</h3>
                    </div>
                    <div className="space-y-4">
                      {expensesByUser.slice(0, 3).map(([usr, amount]) => (
                        <div key={usr}>
                          <div className="flex justify-between text-xs mb-1.5">
                            <span className="font-medium text-slate-500 truncate pr-2">{usr.split(' ')[0]}</span>
                            <span className="font-bold text-slate-800">${amount.toLocaleString('es-CL')}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-[#0ea5e9] h-1.5 rounded-full" style={{width: `${Math.max(5, (amount/totalSpent)*100)}%`}}></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white p-6 flex items-center gap-5">
                    <div className="h-14 w-14 bg-sky-50 border border-sky-100 text-[#38bdf8] rounded-2xl flex items-center justify-center shadow-sm">
                      <DollarSign className="h-7 w-7" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Mi Gasto Total</p>
                      <p className="text-3xl font-black text-slate-800">${totalSpent.toLocaleString('es-CL')}</p>
                    </div>
                  </div>
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white p-6 flex items-center gap-5">
                    <div className="h-14 w-14 bg-slate-50 border border-slate-100 text-slate-400 rounded-2xl flex items-center justify-center shadow-sm">
                      <FileText className="h-7 w-7" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Mis Boletas</p>
                      <p className="text-3xl font-black text-slate-800">{totalInvoices} <span className="text-base font-normal text-slate-400">registradas</span></p>
                    </div>
                  </div>
                </div>
              )}

              {/* History Table */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm bg-white overflow-hidden">
                <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row md:items-end justify-between gap-6">
                  <div>
                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-3">
                      {activeTab === 'admin' ? <><ShieldAlert className="h-5 w-5 text-[#0ea5e9]"/> Auditoría Global</> : <><History className="h-5 w-5 text-slate-400"/> Historial de Rendiciones</>}
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">Explora, filtra y edita los gastos registrados.</p>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
                    {activeTab === 'admin' && (
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 pl-1">Usuario</label>
                        <select 
                          value={filterUser}
                          onChange={(e) => setFilterUser(e.target.value)}
                          className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all sm:w-36 p-2.5 rounded-lg text-sm"
                        >
                          <option value="">Todos</option>
                          {uniqueUsers.map(u => <option key={u} value={u}>{u.split(' ')[0]}</option>)}
                        </select>
                      </div>
                    )}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 pl-1">Departamento</label>
                      <select 
                        value={filterDept}
                        onChange={(e) => setFilterDept(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all sm:w-36 p-2.5 rounded-lg text-sm"
                      >
                        <option value="">Todos</option>
                        <option value="Ventas">Ventas</option>
                        <option value="Gerencia">Gerencia</option>
                        <option value="Operaciones">Operaciones</option>
                        <option value="Administración">Administración</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 pl-1">Centro Costo</label>
                      <select 
                        value={filterCostCenter}
                        onChange={(e) => setFilterCostCenter(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all sm:w-36 p-2.5 rounded-lg text-sm font-mono"
                      >
                        <option value="">Todos</option>
                        {uniqueCostCenters.map(cc => (
                          <option key={cc} value={cc}>{cc}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-end">
                      <button 
                        onClick={fetchHistory} 
                        className="h-[42px] px-4 w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 transition-all rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center"
                        title="Actualizar"
                      >
                        <RefreshCcw className={`h-4 w-4 text-slate-500 ${loadingHistory ? 'animate-spin text-[#38bdf8]' : ''}`} />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="p-0 overflow-x-auto">
                  {loadingHistory ? (
                    <div className="p-20 text-center flex flex-col items-center">
                      <div className="h-16 w-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                        <RefreshCcw className="h-8 w-8 animate-spin text-[#38bdf8]" />
                      </div>
                      <p className="font-semibold text-slate-600 tracking-wide">Sincronizando datos...</p>
                    </div>
                  ) : filteredExpenses.length === 0 ? (
                    <div className="p-20 text-center flex flex-col items-center">
                      <div className="h-20 w-20 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                        <FileText className="h-10 w-10 text-slate-300" />
                      </div>
                      <p className="font-semibold text-slate-600">No hay gastos para mostrar.</p>
                      <p className="text-sm text-slate-400 mt-1">Intenta cambiar los filtros o sube una nueva boleta.</p>
                    </div>
                  ) : (
                    <table className="w-full text-left border-collapse w-full text-left border-collapse">
                      <thead>
                        <tr>
                          <th className="p-5 text-xs">Proyecto / Fecha</th>
                          {activeTab === 'admin' && <th className="p-5 text-xs">Usuario / Depto</th>}
                          <th className="p-5 text-xs">Proveedor</th>
                          <th className="p-5 text-xs text-right">Monto</th>
                          <th className="p-5 text-xs text-center">Boleta</th>
                          <th className="p-5 text-xs text-right">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredExpenses.map((exp) => (
                          <tr key={exp.id} className="group">
                            <td className="p-5">
                              <span className="bg-sky-50 text-[#0284c7] py-1.5 px-3 rounded-lg text-xs font-mono font-bold border border-sky-100 inline-block mb-1.5">
                                {exp.centro_costo}
                              </span>
                              <div className="text-[11px] text-slate-500 font-medium flex items-center gap-1.5">
                                <Calendar className="h-3 w-3" /> {exp.fecha_captura?.substring(0,10)}
                              </div>
                            </td>
                            {activeTab === 'admin' && (
                              <td className="p-5">
                                <p className="text-sm font-semibold text-slate-800">{exp.usuario_nombre}</p>
                                <p className="text-[10px] text-slate-400 uppercase tracking-wider mt-0.5">{exp.departamento}</p>
                              </td>
                            )}
                            <td className="p-5">
                              <p className="text-sm font-semibold text-slate-700">{exp.rut_proveedor}</p>
                              <p className="text-xs text-slate-400 mt-0.5">{exp.fecha_boleta}</p>
                            </td>
                            <td className="p-5 text-sm font-bold text-slate-800 text-right">${parseInt(exp.monto_total || 0).toLocaleString('es-CL')}</td>
                            <td className="p-5 text-center">
                              {exp.link_drive ? (
                                <a href={exp.link_drive} target="_blank" rel="noreferrer" className="inline-flex p-2.5 bg-slate-50 text-[#38bdf8] hover:bg-sky-50 rounded-xl transition-all hover:scale-110 border border-slate-200 shadow-sm" title="Ver Boleta">
                                  <FileText className="h-4 w-4" />
                                </a>
                              ) : (
                                <span className="text-xs text-slate-300">-</span>
                              )}
                            </td>
                            <td className="p-5 text-right">
                              <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                  onClick={() => startEdit(exp)}
                                  className="p-2 text-slate-400 hover:text-[#38bdf8] hover:bg-sky-50 rounded-lg transition-all"
                                  title="Editar Gasto"
                                >
                                  <Edit2 className="h-4 w-4" />
                                </button>
                                <button 
                                  onClick={() => handleDelete(exp.id)}
                                  className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                                  title="Eliminar Gasto"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Edit Modal */}
              {editingExpense && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
                  <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl transform transition-all">
                    <div className="px-6 py-5 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                      <h3 className="font-bold text-slate-800 flex items-center gap-2 text-lg"><Edit2 className="h-5 w-5 text-[#38bdf8]" /> Corregir Gasto</h3>
                      <button onClick={() => setEditingExpense(null)} className="p-1.5 hover:bg-slate-200 rounded-full text-slate-400 transition-colors"><X className="h-5 w-5" /></button>
                    </div>
                    <div className="p-6 space-y-5">
                      <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Centro de Costo</label>
                        <input type="text" value={editForm.centro_costo} onChange={e => setEditForm({...editForm, centro_costo: e.target.value.toUpperCase()})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl font-mono uppercase" />
                      </div>
                      <div className="grid grid-cols-2 gap-5">
                        <div>
                          <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">RUT Proveedor</label>
                          <input type="text" value={editForm.rut_proveedor} onChange={e => setEditForm({...editForm, rut_proveedor: e.target.value})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl" />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Fecha Boleta</label>
                          <input type="text" value={editForm.fecha_boleta} onChange={e => setEditForm({...editForm, fecha_boleta: e.target.value})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl" />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Monto Total ($)</label>
                        <input type="number" value={editForm.monto_total} onChange={e => setEditForm({...editForm, monto_total: e.target.value})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl font-bold text-lg text-[#0284c7]" />
                      </div>
                      <div className="pt-6">
                        <button onClick={handleEditSubmit} className="bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors shadow-sm font-bold tracking-wide w-full py-3.5 rounded-xl text-lg flex justify-center items-center gap-2">
                          Guardar Cambios
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </GoogleOAuthProvider>
  );
}

export default App;
