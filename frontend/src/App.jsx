import React, { useState, useEffect, useMemo } from 'react';
import { 
  Camera, Upload, CheckCircle, FileText, RefreshCcw, DollarSign, Calendar, Hash, 
  User, ShieldAlert, History, Filter, Edit2, Trash2, X, PieChart, Users, Building2, 
  BarChart3, ArrowRight, LogOut, AlertTriangle, ArrowDownCircle, Wallet, AlertCircle, 
  HelpCircle, ChevronDown, HardDriveDownload, Ban, CreditCard, Receipt, FileSpreadsheet 
} from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import axios from 'axios';

const ADMIN_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl", "jorge.salas@e-voltage.cl"];
const APPROVER_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl"];

const HoverDropdown = ({ label, value, options, onChange, className = "" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = React.useRef(null);

  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  const toggleDropdown = () => setIsOpen(!isOpen);

  return (
    <div 
      ref={dropdownRef}
      className={`relative ${isOpen ? 'z-50' : 'z-40'}`}
    >
      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 pl-1">{label}</label>
      <div 
        onClick={toggleDropdown}
        className={`w-full sm:w-36 bg-white border border-slate-300 rounded-lg px-4 py-2 flex items-center justify-between cursor-pointer hover:border-amber-400 hover:ring-2 hover:ring-amber-500/20 transition-all h-[42px] ${className}`}
      >
        <span className="text-sm text-slate-700 truncate mr-2 font-medium">
          {options.find(o => o.value === value)?.label || 'Todos'}
        </span>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </div>
      
      {/* Animated Dropdown Menu */}
      <div 
        className={`absolute top-full left-0 mt-2 w-full sm:w-48 bg-white border border-slate-200 rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.15)] overflow-hidden transition-all duration-300 origin-top ${
          isOpen ? 'opacity-100 scale-y-100 translate-y-0' : 'opacity-0 scale-y-95 -translate-y-2 pointer-events-none'
        }`}
      >
        <div className="py-1.5 max-h-64 overflow-y-auto">
          {options.map((opt, i) => (
            <div
              key={i}
              onClick={() => {
                onChange(opt.value);
                setIsOpen(false);
              }}
              className={`px-4 py-2.5 text-sm cursor-pointer transition-colors flex items-center ${
                value === opt.value 
                  ? 'bg-amber-50 text-amber-700 font-bold border-l-2 border-amber-500' 
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 border-l-2 border-transparent'
              }`}
            >
              {opt.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Donut Chart Component for Rendición por Estado
const StatusDonutChart = ({ pending = 0, approved = 0, rejected = 0, voided = 0 }) => {
  const total = pending + approved + rejected + voided;
  if (total === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-slate-400 text-xs">
        <span>Sin datos de estado</span>
      </div>
    );
  }

  const pPend = Math.round((pending / total) * 100);
  const pAppr = Math.round((approved / total) * 100);
  const pRej = Math.round((rejected / total) * 100);
  const pVoid = Math.max(0, 100 - (pPend + pAppr + pRej));

  // Circumference for r=38 is 2 * PI * 38 = ~238.76
  const C = 238.76;
  const strokePend = (pPend / 100) * C;
  const strokeAppr = (pAppr / 100) * C;
  const strokeRej = (pRej / 100) * C;
  const strokeVoid = (pVoid / 100) * C;

  const offsetAppr = strokePend;
  const offsetRej = strokePend + strokeAppr;
  const offsetVoid = strokePend + strokeAppr + strokeRej;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col items-center justify-between">
      <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 w-full text-center">
        Rendición por Estado
      </h3>

      <div className="relative w-36 h-36 flex items-center justify-center my-2">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle cx="50" cy="50" r="38" fill="transparent" stroke="#f1f5f9" strokeWidth="16" />
          
          {/* Pendiente (Yellow) */}
          {strokePend > 0 && (
            <circle
              cx="50" cy="50" r="38" fill="transparent"
              stroke="#fbbf24" strokeWidth="16"
              strokeDasharray={`${strokePend} ${C - strokePend}`}
              strokeDashoffset="0"
            />
          )}

          {/* Aprobado (Green) */}
          {strokeAppr > 0 && (
            <circle
              cx="50" cy="50" r="38" fill="transparent"
              stroke="#10b981" strokeWidth="16"
              strokeDasharray={`${strokeAppr} ${C - strokeAppr}`}
              strokeDashoffset={`-${offsetAppr}`}
            />
          )}

          {/* Rechazado (Red) */}
          {strokeRej > 0 && (
            <circle
              cx="50" cy="50" r="38" fill="transparent"
              stroke="#f43f5e" strokeWidth="16"
              strokeDasharray={`${strokeRej} ${C - strokeRej}`}
              strokeDashoffset={`-${offsetRej}`}
            />
          )}

          {/* Anulado (Gray) */}
          {strokeVoid > 0 && (
            <circle
              cx="50" cy="50" r="38" fill="transparent"
              stroke="#94a3b8" strokeWidth="16"
              strokeDasharray={`${strokeVoid} ${C - strokeVoid}`}
              strokeDashoffset={`-${offsetVoid}`}
            />
          )}
        </svg>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-black text-slate-800">{total}</span>
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Docs</span>
        </div>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-3 text-[11px] font-semibold text-slate-600 w-full px-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0"></span>
          <span className="truncate">Pendiente {pPend}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0"></span>
          <span className="truncate">Aprobado {pAppr}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0"></span>
          <span className="truncate">Rechazado {pRej}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-400 shrink-0"></span>
          <span className="truncate">Anulado {pVoid}%</span>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('df_gastos_user');
    return saved ? JSON.parse(saved) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('df_gastos_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('df_gastos_user');
    }
  }, [user]);

  const [activeTab, setActiveTab] = useState('scanner'); // 'scanner' | 'history' | 'admin'
  
  // Scanner States
  const [adminStatusFilter, setAdminStatusFilter] = useState('all');
  const [adminSearchQuery, setAdminSearchQuery] = useState('');
  const [transactionType, setTransactionType] = useState(null);
  const [origenFondos, setOrigenFondos] = useState('');
  const [montoCaja, setMontoCaja] = useState('');
  const [montoNC, setMontoNC] = useState('');
  const [clasificacionSinRespaldo, setClasificacionSinRespaldo] = useState('');
  const [capitalEntregado, setCapitalEntregado] = useState(0);
  const [facturaAsociada, setFacturaAsociada] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [file, setFile] = useState(null);
  const [manualFile, setManualFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [fallbackData, setFallbackData] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [costCenter, setCostCenter] = useState("");
  const [department, setDepartment] = useState("");

  // History & Admin States
  const [expenses, setExpenses] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [filterDept, setFilterDept] = useState("");
  const [filterCostCenter, setFilterCostCenter] = useState("");
  const [filterUser, setFilterUser] = useState("");
  const [filterEstado, setFilterEstado] = useState("");
  const [filterTipo, setFilterTipo] = useState("");
  
  // Edit States
  const [editingExpense, setEditingExpense] = useState(null);
  const [editForm, setEditForm] = useState({});

  // Custom UI Dialog
  const [dialog, setDialog] = useState({ isOpen: false, type: 'info', title: '', message: '', onConfirm: null });

  const showConfirm = (title, message, onConfirm) => setDialog({ isOpen: true, type: 'confirm', title, message, onConfirm });
  const showError = (title, message) => setDialog({ isOpen: true, type: 'error', title, message, onConfirm: null });
  const showSuccess = (title, message) => setDialog({ isOpen: true, type: 'success', title, message, onConfirm: null });

  const isAdmin = user && ADMIN_EMAILS.includes(user.email.toLowerCase());
  const isApprover = user && APPROVER_EMAILS.includes(user.email.toLowerCase());

  const login = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const userInfo = await axios.get('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        });
        setUser({ 
          name: userInfo.data.name, 
          email: userInfo.data.email, 
          picture: userInfo.data.picture 
        });
      } catch (err) {
        console.error('Failed to fetch user info', err);
        alert('Error al obtener datos de Google.');
      }
    },
    prompt: 'select_account'
  });

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
    formData.append('skip_ocr', (transactionType === 'Saldo Inicial' || transactionType === 'Ingreso de Dinero' || transactionType === 'Sin Respaldo') ? 'true' : 'false');

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}` + '/upload-receipt', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        setReviewData(response.data.data);
      } else {
        const msg = response.data.error || '';
        if (msg.includes('503') || msg.includes('unavailable')) {
          setError("El servidor está despertando. Por favor intenta de nuevo en unos segundos.");
        } else {
          setError(msg || "Error de lectura en el archivo. Puedes reintentar o ingresar los datos manualmente.");
          if (response.data.data) {
            setFallbackData(response.data.data);
          }
        }
      }
    } catch (err) {
      if (err.message?.includes('Network') || err.message?.includes('timeout')) {
        setError("No se pudo conectar con el servidor. Puede estar despertando, intenta de nuevo en unos segundos.");
      } else {
        setError("Error de conexión con el servidor: " + err.message);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveReceipt = async () => {
    setIsSaving(true);
    setError(null);
    try {
      let finalLinkDrive = reviewData.link_drive;
      
      if (manualFile && !finalLinkDrive) {
        const formData = new FormData();
        formData.append('file', manualFile);
        formData.append('userName', user.name);
        formData.append('userEmail', user.email);
        formData.append('department', department || reviewData.departamento);
        formData.append('costCenter', costCenter || reviewData.centro_costo);
        formData.append('skip_ocr', 'true');
        
        const uploadRes = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/upload-receipt`, formData, {
           headers: { 'Content-Type': 'multipart/form-data' }
        });
        if (uploadRes.data.success && uploadRes.data.data.link_drive) {
           finalLinkDrive = uploadRes.data.data.link_drive;
        } else {
           setError("Error subiendo el archivo adjunto.");
           setIsSaving(false);
           return;
        }
      }

      const payload = { 
        ...reviewData, 
        link_drive: finalLinkDrive, 
        tipo_transaccion: transactionType, 
        origen_fondos: origenFondos, 
        monto_caja: montoCaja ? parseFloat(montoCaja) : 0,
        monto_nc: montoNC ? parseFloat(montoNC) : 0,
        clasificacion_sin_respaldo: clasificacionSinRespaldo,
        factura_asociada: facturaAsociada, 
        descripcion: descripcion 
      };
      const response = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/save-receipt`, payload);
      if (response.data.success) {
        setResult(response.data.data);
        setReviewData(null);
        setManualFile(null);
      } else {
        setError("Error guardando: " + response.data.error);
      }
    } catch (err) {
      setError("Error de red guardando la boleta.");
    } finally {
      setIsSaving(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setManualFile(null);
    setResult(null);
    setReviewData(null);
    setError(null);
    setTransactionType(null);
    setOrigenFondos('');
    setFacturaAsociada('');
    setDescripcion('');
  };

  const resetAll = () => {
    setFile(null);
    setResult(null);
    setReviewData(null);
    setError(null);
    setCostCenter("");
    setDepartment("");
  };

  const goHome = () => {
    setActiveTab('scanner');
    setTransactionType(null);
    resetAll();
    resetForm();
  };

  const fetchHistory = async () => {
    if (!user) return;
    setLoadingHistory(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      let response;
      if (activeTab === 'admin') {
        response = await axios.get(
          `${API_URL}/admin/history?email=${encodeURIComponent(user.email)}`,
          { headers: { 'X-User-Email': user.email } }
        );
      } else {
        response = await axios.get(
          `${API_URL}/history?email=${encodeURIComponent(user.email)}`
        );
      }

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
    if (user && activeTab !== 'admin') {
      const fetchCapital = async () => {
        try {
          const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const res = await axios.get(`${API_URL}/capital/${encodeURIComponent(user.email)}`);
          if (res.data.success) setCapitalEntregado(parseFloat(res.data.monto_asignado) || 0);
        } catch (e) {
          console.error("Error fetching capital", e);
        }
      };
      fetchCapital();
    }
  }, [user, activeTab]);

  useEffect(() => {
    if ((activeTab === 'history' || activeTab === 'admin') && user) {
      fetchHistory();
    }
  }, [activeTab, user]);

  const handleUpdateStatus = async (id, nuevoEstado) => {
    let comentarios = "";
    if (nuevoEstado === 'Rechazado' || nuevoEstado === 'Anulado') {
      const motivo = window.prompt(`Por favor, ingresa el motivo del ${nuevoEstado === 'Anulado' ? 'anulación' : 'rechazo'}:`);
      if (motivo === null) return;
      comentarios = motivo;
    }
    
    try {
      await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/update-expense-status`, {
        id,
        estado: nuevoEstado,
        comentarios_revisor: comentarios
      }, {
        headers: { 'X-User-Email': user?.email || '' }
      });
      fetchHistory();
    } catch (err) {
      console.error("Error updating status", err);
      showError("Error", err.response?.data?.detail || "Hubo un error al actualizar el estado");
    }
  };

  const handleDelete = async (id) => {
    showConfirm(
      "Eliminar Registro", 
      "¿Estás seguro de que quieres eliminar este gasto? Esta acción no se puede deshacer.", 
      async () => {
        setDialog({ isOpen: false });
        try {
          await axios.delete(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${id}`, {
            headers: { 'X-User-Email': user?.email || '' }
          });
          fetchHistory();
        } catch (err) {
          console.error("Error deleting", err);
          showError("Error", err.response?.data?.detail || "Hubo un error al eliminar el registro.");
        }
      }
    );
  };

  const startEdit = (exp) => {
    setEditingExpense(exp);
    setEditForm({
      departamento: exp.departamento,
      centro_costo: exp.centro_costo,
      rut_proveedor: exp.rut_proveedor,
      fecha_boleta: exp.fecha_boleta,
      monto_total: exp.monto_total,
      tipo_transaccion: exp.tipo_transaccion || 'Boleta',
      origen_fondos: exp.origen_fondos || 'Caja Principal',
      monto_caja: exp.monto_caja || 0,
      monto_nc: exp.monto_nc || 0,
      clasificacion_sin_respaldo: exp.clasificacion_sin_respaldo || '',
      factura_asociada: exp.factura_asociada || '',
      descripcion: exp.descripcion || '',
      comentarios_revisor: exp.comentarios_revisor || '',
      estado: exp.estado || 'Pendiente de Revisión'
    });
  };

  const handleEditSubmit = async () => {
    try {
      await axios.put(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/expense/${editingExpense.id}`, 
        editForm,
        { headers: { 'X-User-Email': user?.email || '' } }
      );
      setEditingExpense(null);
      fetchHistory();
    } catch (err) {
      console.error("Error updating", err);
      showError("Error", err.response?.data?.detail || "Error al actualizar el gasto");
    }
  };

  const handleExport = async () => {
    const isFiltered = filterDept || filterCostCenter || filterUser;
    const mensaje = isFiltered 
      ? `Estás a punto de exportar a Google Sheets SOLO los ${filteredExpenses.length} registros que cumplen con tus filtros actuales.\n\nEsto sobrescribirá la planilla en Drive.\n\n¿Deseas continuar?`
      : `Estás a punto de exportar TODOS los registros (${filteredExpenses.length} en total) a Google Sheets.\n\nEsto sobrescribirá la planilla en Drive.\n\n¿Deseas continuar?`;
      
    showConfirm("Confirmar Exportación", mensaje, async () => {
      setDialog({ isOpen: false });
      setIsExporting(true);
      try {
        const headers = [
          "ID Gasto", 
          "Estado", 
          "Fecha Captura", 
          "Usuario", 
          "Email", 
          "Departamento", 
          "Centro de Costo", 
          "RUT Proveedor", 
          "Fecha Boleta", 
          "Monto Total", 
          "Monto Caja Principal",
          "Monto Casa Comercial (NC)",
          "IVA", 
          "Link Boleta",
          "Tipo Transacción",
          "Origen Fondos",
          "N° Doc / Fact. Asociada",
          "Descripción",
          "Comentarios Revisor"
        ];

        const dataRows = filteredExpenses.map(exp => [
          exp.id,
          exp.estado || "Pendiente de Revisión",
          exp.fecha_captura || "",
          exp.usuario_nombre || "",
          exp.usuario_email || "",
          exp.departamento || "",
          exp.centro_costo || "",
          exp.rut_proveedor || "",
          exp.fecha_boleta || "",
          exp.monto_total || 0,
          exp.monto_caja || 0,
          exp.monto_nc || 0,
          exp.iva || 0,
          exp.link_drive || "",
          exp.tipo_transaccion || "Boleta",
          exp.origen_fondos || "Caja Principal",
          exp.factura_asociada || "",
          exp.descripcion || "",
          exp.comentarios_revisor || ""
        ]);

        const rows = [headers, ...dataRows];

        const response = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/export-sheets`, { rows });
        if (response.data.success) {
          showSuccess("¡Exportación Exitosa!", `Se han exportado ${dataRows.length} registros a Google Sheets correctamente.`);
        } else {
          showError("Error de Exportación", response.data.error || "Ocurrió un error en el servidor.");
        }
      } catch (err) {
        console.error("Export error", err);
        showError("Error de Red", "No se pudo conectar con el servidor para exportar a Sheets.");
      } finally {
        setIsExporting(false);
      }
    });
  };

  const uniqueCostCenters = [...new Set(expenses.map(exp => exp.centro_costo))].filter(Boolean).sort();
  const uniqueUsers = [...new Set(expenses.map(exp => exp.usuario_nombre))].filter(Boolean).sort();
  const uniqueEstados = [...new Set(expenses.map(exp => exp.estado || 'Pendiente de Revisión'))].filter(Boolean).sort();
  const uniqueTipos = [...new Set(expenses.map(exp => exp.tipo_transaccion || 'Boleta'))].filter(Boolean).sort();

  const filteredExpenses = expenses.filter(exp => {
    const matchDept = filterDept ? exp.departamento === filterDept : true;
    const matchCC = filterCostCenter ? exp.centro_costo === filterCostCenter : true;
    const matchUser = filterUser ? exp.usuario_nombre === filterUser : true;
    const matchEstado = filterEstado ? (exp.estado || 'Pendiente de Revisión') === filterEstado : true;
    const matchTipo = filterTipo ? (exp.tipo_transaccion || 'Boleta') === filterTipo : true;
    return matchDept && matchCC && matchUser && matchEstado && matchTipo;
  });

  const isRejectedOrVoid = (estado) => {
    const s = (estado || '').toLowerCase().trim();
    return s === 'rechazado' || s === 'rechazada' || s === 'anulado' || s === 'anulada';
  };

  const isApprovedStatus = (estado) => {
    const s = (estado || '').toLowerCase().trim();
    return s === 'aprobado' || s === 'aprobada';
  };

  const isPendingStatus = (estado) => {
    const s = (estado || '').toLowerCase().trim();
    return s === 'pendiente de revisión' || s === 'pendiente' || s === 'pendiente_de_aprobacion' || s === 'pendiente de aprobación';
  };

  // KPIs Financieros Segregados DealFlow v2.4 (3 Cajas Contables + Ciclo de Aprobación de Finanzas)
  const finanzas = useMemo(() => {
    // 1. Caja 1: Fondo Principal (Liquidez Bancaria)
    let totalAsignadoCaja = activeTab === 'admin' ? 0 : capitalEntregado;
    let gastosAprobadosCaja = 0;
    let pendienteAprobacionCaja = 0;

    // 2. Caja 2: Casa Comercial (Notas de Crédito)
    let totalNotasCredito = 0;
    let gastosAprobadosNC = 0;
    let pendienteAprobacionNC = 0;

    // 3. Caja 3: Por Recuperar por Liquidación (Gastos Sin Respaldo / Nómina)
    let fondosSinRespaldoTotal = 0;
    let fondosSinRespaldoPendiente = 0;
    let fondosSinRespaldoAprobado = 0;

    // Métricas Globales / Admin
    let totalGastadoEmpresa = 0;
    let ivaAcumulado = 0;

    // Donut chart counts
    let countPendiente = 0;
    let countAprobado = 0;
    let countRechazado = 0;
    let countAnulado = 0;
    let totalMontoFiltered = 0;

    filteredExpenses.forEach(exp => {
      const monto = parseFloat(exp.monto_total) || 0;
      const mCaja = parseFloat(exp.monto_caja) || 0;
      const mNC = parseFloat(exp.monto_nc) || 0;
      const iva = parseFloat(exp.iva) || 0;
      const estadoNorm = (exp.estado || '').toLowerCase().trim();
      const isAppr = isApprovedStatus(exp.estado);
      const isPend = isPendingStatus(exp.estado);
      const isRej = estadoNorm === 'rechazado' || estadoNorm === 'rechazada';
      const isVoid = estadoNorm === 'anulado' || estadoNorm === 'anulada';

      // Conteo para gráfico de estados
      if (isAppr) countAprobado++;
      else if (isPend) countPendiente++;
      else if (isRej) countRechazado++;
      else if (isVoid) countAnulado++;

      totalMontoFiltered += monto;

      // Si está Rechazado o Anulado, no afecta los saldos vivos de las cajas
      if (isRejectedOrVoid(exp.estado)) return;

      // Inyecciones de Fondos / Saldos Iniciales (Caja 1)
      if (exp.tipo_transaccion === 'Saldo Inicial' || exp.tipo_transaccion === 'Ingreso de Dinero') {
        totalAsignadoCaja += monto;
      }
      // Notas de Crédito (Caja 2)
      else if (exp.tipo_transaccion === 'Nota de Crédito') {
        totalNotasCredito += monto;
        if (isAppr) ivaAcumulado += iva;
      }
      // Gastos Operativos / Boletas / Facturas / Sin Respaldo
      else {
        if (isAppr) {
          totalGastadoEmpresa += monto;
          ivaAcumulado += iva;
        }

        // Determinar cómo se financia este gasto (Caja vs NC)
        let deducirCaja = 0;
        let deducirNC = 0;

        if (exp.origen_fondos === 'Fondos Mixtos') {
          deducirCaja = mCaja;
          deducirNC = mNC;
        } else if (exp.origen_fondos === 'Casa Comercial') {
          deducirNC = monto;
        } else {
          deducirCaja = monto;
        }

        // Impacto en Caja 1 (Fondo Principal)
        if (isAppr) {
          gastosAprobadosCaja += deducirCaja;
        } else if (isPend) {
          pendienteAprobacionCaja += deducirCaja;
        }

        // Impacto en Caja 2 (Casa Comercial)
        if (isAppr) {
          gastosAprobadosNC += deducirNC;
        } else if (isPend) {
          pendienteAprobacionNC += deducirNC;
        }

        // Caja 3: Por Recuperar por Liquidación (Gastos Sin Respaldo)
        if (exp.tipo_transaccion === 'Gasto Sin Respaldo' || exp.tipo_transaccion === 'Sin Respaldo' || exp.origen_fondos === 'Cuentas por Recuperar') {
          fondosSinRespaldoTotal += monto;
          if (isPend) fondosSinRespaldoPendiente += monto;
          if (isAppr) fondosSinRespaldoAprobado += monto;
        }
      }
    });

    // Fórmulas v2.4:
    // CAJA 1:
    const totalARendir = totalAsignadoCaja - gastosAprobadosCaja;
    const saldoPorRendir = totalARendir - pendienteAprobacionCaja;

    // CAJA 2:
    const totalCasaComercial = totalNotasCredito - gastosAprobadosNC;
    const saldoEnCasaComercial = totalCasaComercial - pendienteAprobacionNC;

    // CAJA 3:
    const porRecuperarLiquidacion = fondosSinRespaldoTotal;

    const totalRegistros = countPendiente + countAprobado + countRechazado + countAnulado;
    const pctPendiente = totalRegistros > 0 ? Math.round((countPendiente / totalRegistros) * 100) : 0;
    const pctAprobado = totalRegistros > 0 ? Math.round((countAprobado / totalRegistros) * 100) : 0;
    const pctRechazado = totalRegistros > 0 ? Math.round((countRechazado / totalRegistros) * 100) : 0;
    const pctAnulado = totalRegistros > 0 ? Math.max(0, 100 - (pctPendiente + pctAprobado + pctRechazado)) : 0;

    return {
      totalARendir,
      pendienteAprobacionCaja,
      saldoPorRendir,
      totalCasaComercial,
      saldoEnCasaComercial,
      pendienteAprobacionNC,
      porRecuperarLiquidacion,
      fondosSinRespaldoPendiente,
      fondosSinRespaldoAprobado,
      totalGastadoEmpresa,
      ivaAcumulado,
      totalMontoFiltered,
      countPendiente,
      countAprobado,
      countRechazado,
      countAnulado,
      totalRegistros,
      pctPendiente,
      pctAprobado,
      pctRechazado,
      pctAnulado
    };
  }, [filteredExpenses, capitalEntregado, activeTab]);

  const totalSpent = finanzas.totalGastadoEmpresa;
  const ivaAcumulado = finanzas.ivaAcumulado;
  const totalInvoices = filteredExpenses.length;

  const isValidExpense = (exp) => {
    return !isRejectedOrVoid(exp.estado) && 
           exp.tipo_transaccion !== 'Saldo Inicial' && 
           exp.tipo_transaccion !== 'Ingreso de Dinero' && 
           exp.tipo_transaccion !== 'Nota de Crédito';
  };

  const expensesByDept = useMemo(() => {
    const res = {};
    filteredExpenses.forEach(exp => {
      if (isValidExpense(exp)) {
        res[exp.departamento] = (res[exp.departamento] || 0) + (parseFloat(exp.monto_total) || 0);
      }
    });
    return Object.entries(res).sort((a,b) => b[1] - a[1]);
  }, [filteredExpenses]);

  const expensesByUser = useMemo(() => {
    const res = {};
    filteredExpenses.forEach(exp => {
      if (isValidExpense(exp)) {
        res[exp.usuario_nombre] = (res[exp.usuario_nombre] || 0) + (parseFloat(exp.monto_total) || 0);
      }
    });
    return Object.entries(res).sort((a,b) => b[1] - a[1]);
  }, [filteredExpenses]);

  const expensesByCostCenter = useMemo(() => {
    const res = {};
    filteredExpenses.forEach(exp => {
      if (exp.centro_costo && isValidExpense(exp)) {
        res[exp.centro_costo] = (res[exp.centro_costo] || 0) + (parseFloat(exp.monto_total) || 0);
      }
    });
    return Object.entries(res).sort((a,b) => b[1] - a[1]);
  }, [filteredExpenses]);

  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-sky-100 selection:text-sky-900 pb-16">
        
        {/* HEADER */}
        <header className="bg-white border-b border-slate-100 sticky top-0 z-20">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            
            {/* Left: App Branding */}
            <button onClick={goHome} className="flex items-center gap-3 hover:opacity-80 transition-opacity text-left outline-none" title="Volver al Inicio">
              <img src="/icon-192.png" alt="DealFlow Gastos" className="shrink-0 h-10 w-10 rounded-[10px] shadow-sm" />
              
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h1 className="text-[17px] font-bold text-[#1e293b] tracking-tight leading-none">DealFlow Gastos</h1>
                  <span className="bg-[#f1f5f9] text-[#64748b] text-[10px] font-bold px-1.5 py-0.5 rounded leading-none">v2.4</span>
                </div>
                <p className="text-[10px] uppercase tracking-widest text-[#94a3b8] font-bold mt-1 leading-none">Plataforma de Rendiciones</p>
              </div>
            </button>

            {/* Right: Company Logo Pill & User Profile */}
            <div className="flex items-center gap-5 shrink-0">
              <div className="hidden sm:flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                <img src="/logo.png" alt="E-Voltage" className="object-contain shrink-0 h-6" />
                <span className="text-[11px] text-slate-400 font-medium border-l border-slate-200 pl-3">Powered by DealFlow</span>
              </div>
              
              {user && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
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
                  <button
                    onClick={() => {
                      setUser(null);
                      setFile(null);
                      setResult(null);
                      setError(null);
                    }}
                    title="Cerrar sesión"
                    className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100 flex items-center justify-center"
                  >
                    <LogOut className="h-4.5 w-4.5" />
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* TABS */}
          {user && (
            <div className="max-w-7xl mx-auto px-4 flex gap-2 sm:gap-3 mt-4 mb-2">
              <button 
                onClick={() => {setActiveTab('scanner'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                className={`flex-1 px-2 sm:px-4 py-2 rounded-lg font-medium text-[12px] sm:text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'scanner' ? 'bg-indigo-50 text-indigo-600 shadow-sm border border-indigo-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
              >
                <div className="flex items-center justify-center gap-1.5 sm:gap-2">
                  <Camera className="h-4 w-4" /> Registrar Documento
                </div>
              </button>
              <button 
                onClick={() => {setActiveTab('history'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                className={`flex-1 px-2 sm:px-4 py-2 rounded-lg font-medium text-[12px] sm:text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'history' ? 'bg-purple-50 text-purple-600 shadow-sm border border-purple-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
              >
                <div className="flex items-center justify-center gap-1.5 sm:gap-2">
                  <History className="h-4 w-4" /> Mi Historial
                </div>
              </button>
              {isAdmin && (
                <button 
                  onClick={() => {setActiveTab('admin'); setFilterDept(''); setFilterCostCenter(''); setFilterUser('');}}
                  className={`flex-1 px-2 sm:px-4 py-2 rounded-lg font-medium text-[12px] sm:text-[13px] whitespace-nowrap transition-all duration-200 ${activeTab === 'admin' ? 'bg-sky-50 text-sky-600 shadow-sm border border-sky-100' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
                >
                  <div className="flex items-center justify-center gap-1.5 sm:gap-2">
                    <PieChart className="h-4 w-4" /> Panel Admin
                  </div>
                </button>
              )}
            </div>
          )}
        </header>

        <main className="max-w-7xl mx-auto px-4 py-8">
          {!user ? (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 flex flex-col items-center text-center max-w-md mx-auto mt-16 bg-white">
              <img src="/icon-192.png" alt="DealFlow Gastos" className="h-20 w-20 rounded-2xl shadow-md mb-6" />
              <h2 className="text-3xl font-bold text-slate-800 mb-3">Acceso Restringido</h2>
              <p className="text-slate-500 mb-8 leading-relaxed">Inicia sesión con tu cuenta corporativa para gestionar y rendir gastos.</p>
              <div className="transform hover:scale-105 transition-transform duration-300">
                <button
                  onClick={() => login()}
                  className="flex items-center gap-3 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-medium py-2.5 px-6 rounded-full shadow-sm transition-colors"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                  Acceder con Google
                </button>
              </div>
            </div>
          ) : activeTab === 'scanner' ? (
            /* TAB SCANNER */
            !transactionType ? (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-4xl mx-auto p-8 mt-4">
                <div className="text-center mb-10">
                  <h2 className="text-3xl font-black text-slate-800 mb-3 tracking-tight">¿Qué acción deseas realizar?</h2>
                  <p className="text-slate-500 font-medium">Selecciona el tipo de transacción para continuar.</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2 mb-4">Rendición de Gastos</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <button onClick={() => setTransactionType('Boleta')} className="group p-4 bg-white border-2 border-slate-100 hover:border-[#38bdf8] rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md">
                        <div className="h-10 w-10 bg-sky-50 text-[#38bdf8] rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><FileText className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm">Rendición por Boleta</span>
                      </button>
                      
                      <button onClick={() => setTransactionType('Factura')} className="group p-4 bg-white border-2 border-slate-100 hover:border-[#38bdf8] rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md">
                        <div className="h-10 w-10 bg-sky-50 text-[#38bdf8] rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><FileText className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm">Rendición por Factura</span>
                      </button>
                      
                      <button onClick={() => setTransactionType('Sin Respaldo')} className="group p-4 bg-white border-2 border-slate-100 hover:border-amber-400 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md sm:col-span-2">
                        <div className="h-10 w-10 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><AlertTriangle className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm">Gasto Sin Respaldo</span>
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2 mb-4">Gestión de Fondos</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <button onClick={() => setTransactionType('Ingreso de Dinero')} className="group p-4 bg-white border-2 border-slate-100 hover:border-emerald-400 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md">
                        <div className="h-10 w-10 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><ArrowDownCircle className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm text-center">Ingreso de Dinero</span>
                      </button>
                      
                      <button onClick={() => setTransactionType('Saldo Inicial')} className="group p-4 bg-white border-2 border-slate-100 hover:border-emerald-400 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md">
                        <div className="h-10 w-10 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><Wallet className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm text-center">Saldo Inicial</span>
                      </button>
                      
                      <button onClick={() => setTransactionType('Nota de Crédito')} className="group p-4 bg-white border-2 border-slate-100 hover:border-purple-400 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:shadow-md sm:col-span-2">
                        <div className="h-10 w-10 bg-purple-50 text-purple-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"><RefreshCcw className="h-5 w-5" /></div>
                        <span className="font-bold text-slate-700 text-sm">Nota de Crédito</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : !result ? (
              reviewData ? (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-lg mx-auto">
                  <div className="p-8">
                    <div className="flex justify-between items-center mb-6">
                      <h2 className="text-2xl font-bold text-slate-800">Completar Datos</h2>
                      <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-xs font-bold uppercase">{transactionType}</span>
                    </div>
                    
                    <div className="space-y-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">RUT Proveedor</label>
                          <input type="text" value={reviewData.rut_proveedor} onChange={(e) => setReviewData({...reviewData, rut_proveedor: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm" placeholder="Opcional" />
                        </div>
                        {transactionType !== 'Nota de Crédito' && (
                          <div>
                            <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">N° Documento</label>
                            <input type="text" value={facturaAsociada} onChange={(e) => setFacturaAsociada(e.target.value)} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm" placeholder="Opcional" />
                          </div>
                        )}
                        {transactionType === 'Nota de Crédito' && (
                          <div>
                            <label className="block text-xs font-bold text-slate-500 mb-1 uppercase text-purple-600">Factura Asociada</label>
                            <input type="text" value={facturaAsociada} onChange={(e) => setFacturaAsociada(e.target.value)} className="w-full bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-sm font-bold" />
                          </div>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Monto Total</label>
                          <input type="number" value={reviewData.monto_total} onChange={(e) => {
                              const val = parseFloat(e.target.value) || 0;
                              const applyIva = transactionType === 'Factura' || transactionType === 'Nota de Crédito';
                              setReviewData({...reviewData, monto_total: val, iva: applyIva ? Math.round((val * 19) / 119) : 0});
                            }} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-bold text-sky-600" />
                        </div>
                        {(transactionType === 'Factura' || transactionType === 'Nota de Crédito') && (
                          <div>
                            <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">IVA Calculado</label>
                            <input type="number" value={reviewData.iva} onChange={(e) => setReviewData({...reviewData, iva: parseFloat(e.target.value) || 0})} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm" />
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Fecha</label>
                        <input type="date" value={reviewData.fecha_boleta} onChange={(e) => setReviewData({...reviewData, fecha_boleta: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm" />
                      </div>

                      {origenFondos === 'Fondos Mixtos' && (
                        <div className="pt-3 border-t border-slate-100 mt-4 bg-amber-50/50 p-4 rounded-xl border border-amber-100 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Desglose Pago Mixto</span>
                            <span className="text-[11px] font-bold text-slate-500">Total: ${parseFloat(reviewData.monto_total || 0).toLocaleString('es-CL')}</span>
                          </div>
                          
                          <div>
                            <label className="block text-xs font-bold text-emerald-700 mb-1 uppercase">1. Monto Caja Principal (Liquidez Real)</label>
                            <input 
                              type="number" 
                              value={montoCaja} 
                              onChange={(e) => setMontoCaja(e.target.value)} 
                              placeholder="Ej: 50000" 
                              className="w-full bg-white border border-emerald-300 rounded-lg px-3 py-2 text-sm font-bold text-emerald-800 outline-none focus:ring-2 focus:ring-emerald-500/20" 
                            />
                          </div>
                          
                          <div>
                            <label className="block text-xs font-bold text-purple-700 mb-1 uppercase">2. Monto Nota de Crédito (Saldo Tienda)</label>
                            <input 
                              type="number" 
                              value={montoNC} 
                              onChange={(e) => setMontoNC(e.target.value)} 
                              placeholder="Ej: 20000" 
                              className="w-full bg-white border border-purple-300 rounded-lg px-3 py-2 text-sm font-bold text-purple-800 outline-none focus:ring-2 focus:ring-purple-500/20" 
                            />
                          </div>

                          {(() => {
                            const valCaja = parseFloat(montoCaja) || 0;
                            const valNC = parseFloat(montoNC) || 0;
                            const totalDoc = parseFloat(reviewData.monto_total) || 0;
                            const suma = valCaja + valNC;
                            const diff = totalDoc - suma;
                            const isValid = Math.abs(diff) <= 0.01 && valCaja > 0 && valNC > 0;

                            if (isValid) {
                              return (
                                <div className="p-2 bg-emerald-100/80 border border-emerald-300 rounded-lg text-emerald-800 text-xs font-bold flex items-center gap-1.5">
                                  <CheckCircle className="h-4 w-4 shrink-0" />
                                  <span>Desglose cuadrado correctamente: ${suma.toLocaleString('es-CL')}</span>
                                </div>
                              );
                            } else {
                              return (
                                <div className="p-2.5 bg-rose-100/80 border border-rose-300 rounded-lg text-rose-700 text-xs font-bold space-y-0.5">
                                  <div className="flex items-center gap-1.5">
                                    <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600" />
                                    <span>Suma actual: ${suma.toLocaleString('es-CL')} de ${totalDoc.toLocaleString('es-CL')}</span>
                                  </div>
                                  <p className="text-[11px] font-medium text-rose-600 pl-5.5">
                                    {diff > 0 ? `Faltan $${diff.toLocaleString('es-CL')} por asignar.` : `Excedido por $${Math.abs(diff).toLocaleString('es-CL')}.`}
                                  </p>
                                </div>
                              );
                            }
                          })()}
                        </div>
                      )}

                      {transactionType === 'Sin Respaldo' && (
                        <div className="pt-2 border-t border-slate-100 mt-4">
                          <label className="block text-xs font-bold text-rose-500 mb-1 uppercase">Clasificación Sin Respaldo (Obligatorio)</label>
                          <select 
                            value={clasificacionSinRespaldo} 
                            onChange={(e) => setClasificacionSinRespaldo(e.target.value)} 
                            className="w-full bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 text-sm font-bold outline-none"
                          >
                            <option value="" disabled>Seleccione Clasificación...</option>
                            <option value="Viáticos">Viáticos</option>
                            <option value="Bonos por Movilización">Bonos por Movilización</option>
                            <option value="Otros Gastos Operativos">Otros Gastos Operativos</option>
                          </select>
                        </div>
                      )}

                      <div className="pt-2 border-t border-slate-100 mt-4">
                        <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Observaciones {transactionType === 'Sin Respaldo' && <span className="text-rose-500">(Obligatorio)</span>}</label>
                        <textarea 
                          value={descripcion}
                          onChange={(e) => setDescripcion(e.target.value)}
                          placeholder={transactionType === 'Sin Respaldo' ? "Justificación mandatoria para Finanzas..." : "Opcional. Describe el motivo o detalles del gasto..."}
                          rows="2"
                          className={`w-full bg-white border ${transactionType === 'Sin Respaldo' && !descripcion ? 'border-rose-300' : 'border-slate-300'} rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 transition-all text-sm`}
                        ></textarea>
                      </div>

                      {!reviewData.link_drive && (
                        <div className="pt-4 border-t border-slate-100">
                          <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Adjuntar Documento (Opcional)</label>
                          <input 
                            type="file" 
                            accept="image/*,application/pdf"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                setManualFile(e.target.files[0]);
                              } else {
                                setManualFile(null);
                              }
                            }}
                            className="w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100 transition-colors"
                          />
                          {manualFile && <p className="text-xs text-sky-600 font-bold mt-2">Archivo listo para subir: {manualFile.name}</p>}
                        </div>
                      )}

                    </div>

                    <button 
                      onClick={handleSaveReceipt}
                      disabled={
                        isSaving || 
                        (transactionType === 'Nota de Crédito' && !facturaAsociada.trim()) || 
                        (transactionType === 'Sin Respaldo' && (!clasificacionSinRespaldo || !descripcion.trim())) ||
                        (origenFondos === 'Fondos Mixtos' && (
                          !montoCaja || !montoNC || 
                          Math.abs(((parseFloat(montoCaja) || 0) + (parseFloat(montoNC) || 0)) - (parseFloat(reviewData.monto_total) || 0)) > 0.01
                        ))
                      }
                      className={`mt-8 w-full py-4 rounded-xl font-bold flex items-center justify-center gap-3 text-lg ${
                        isSaving || 
                        (transactionType === 'Nota de Crédito' && !facturaAsociada.trim()) || 
                        (transactionType === 'Sin Respaldo' && (!clasificacionSinRespaldo || !descripcion.trim())) ||
                        (origenFondos === 'Fondos Mixtos' && (
                          !montoCaja || !montoNC || 
                          Math.abs(((parseFloat(montoCaja) || 0) + (parseFloat(montoNC) || 0)) - (parseFloat(reviewData.monto_total) || 0)) > 0.01
                        ))
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                        : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm tracking-wide transition-colors'
                      }`}
                    >
                      {isSaving ? (
                        <><RefreshCcw className="h-6 w-6 animate-spin" /> Guardando...</>
                      ) : (
                        <><CheckCircle className="h-6 w-6" /> Aprobar y Guardar</>
                      )}
                    </button>
                    {error && <div className="mt-4 text-red-500 text-sm font-medium text-center">{error}</div>}
                    <button onClick={resetForm} className="w-full mt-4 py-2 text-slate-400 hover:text-slate-600 text-sm font-medium transition-colors">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-lg mx-auto bg-white mt-4">
                <div className="p-8">
                  <div className="text-center mb-6 relative">
                    <button onClick={() => setTransactionType(null)} className="absolute left-0 top-0 p-2 text-slate-400 hover:text-slate-700 bg-slate-50 rounded-full">
                      <ArrowRight className="h-5 w-5 rotate-180" />
                    </button>
                    <h2 className="text-2xl font-bold text-slate-800 mb-1">{transactionType}</h2>
                    <p className="text-slate-500 text-xs uppercase tracking-widest">
                      {['Boleta', 'Factura', 'Nota de Crédito'].includes(transactionType) ? 'Sube el documento para extraer los datos' : 'Adjunta un comprobante (opcional)'}
                    </p>
                  </div>
                  
                  <div className="w-full mb-5">
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Departamento</label>
                    <select 
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3.5 rounded-xl text-sm"
                    >
                      <option value="">-- Selecciona --</option>
                      <option value="Ventas">Ventas</option>
                      <option value="Gerencia">Gerencia</option>
                      <option value="Operaciones">Operaciones</option>
                      <option value="Administración">Administración</option>
                    </select>
                  </div>

                  <div className="w-full mb-6">
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Centro de Costo</label>
                    <input 
                      type="text"
                      value={costCenter}
                      onChange={(e) => setCostCenter(e.target.value.toUpperCase())}
                      placeholder="Ej: OEV-EXT-260008"
                      className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3.5 rounded-xl text-sm uppercase"
                    />
                  </div>

                  {transactionType === 'Nota de Crédito' && (
                    <div className="w-full mb-6">
                      <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider text-purple-600">N° Factura Asociada (Obligatorio)</label>
                      <input 
                        type="text"
                        value={facturaAsociada}
                        onChange={(e) => setFacturaAsociada(e.target.value)}
                        placeholder="Ej: 123456"
                        className="w-full bg-purple-50 border border-purple-200 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-purple-500/20 text-sm font-bold"
                      />
                    </div>
                  )}

                  {(transactionType === 'Boleta' || transactionType === 'Factura' || transactionType === 'Sin Respaldo') && (
                    <div className="w-full mb-6">
                      <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">¿Origen del Pago?</label>
                      <select 
                        value={origenFondos}
                        onChange={(e) => setOrigenFondos(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all text-sm font-semibold text-slate-700"
                      >
                        <option value="" disabled>Selecciona el origen del pago...</option>
                        <option value="Caja Principal">Fondos por Rendir (Cargo a Caja Principal)</option>
                        <option value="Casa Comercial">Nota de Crédito (Cargo a Casa Comercial)</option>
                        <option value="Fondos Mixtos">Fondos Mixtos (Caja + Comercial)</option>
                      </select>
                    </div>
                  )}

                  <label className={`upload-area w-full h-48 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center cursor-pointer transition-all ${file ? 'border-[#38bdf8] bg-sky-50' : 'border-slate-300 hover:bg-slate-50'} ${isProcessing ? 'pulse-animation' : ''}`}>
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
                      accept="image/*,application/pdf" 
                      capture="environment" 
                      className="hidden" 
                      onChange={handleFileChange}
                    />
                  </label>

                  {!file && (
                     <button onClick={() => {
                        if (!department) {
                          setError("Por favor selecciona un Departamento antes de continuar.");
                          return;
                        }
                        if (!costCenter) {
                          setError("Por favor ingresa un Centro de Costo antes de continuar.");
                          return;
                        }
                        setError(null);
                        setReviewData({
                          id: crypto.randomUUID(),
                          usuario_nombre: user.name,
                          usuario_email: user.email,
                          departamento: department,
                          centro_costo: costCenter,
                          rut_proveedor: '', 
                          fecha_boleta: new Date().toISOString().split('T')[0], 
                          monto_total: 0, 
                          iva: 0, 
                          link_drive: ''
                        });
                     }} 
                     disabled={(['Boleta', 'Factura', 'Sin Respaldo'].includes(transactionType) && !origenFondos) || (transactionType === 'Nota de Crédito' && !facturaAsociada.trim())}
                     className={`w-full mt-3 py-2 font-medium text-sm transition-colors ${((['Boleta', 'Factura', 'Sin Respaldo'].includes(transactionType) && !origenFondos) || (transactionType === 'Nota de Crédito' && !facturaAsociada.trim())) ? 'text-slate-300 cursor-not-allowed' : 'text-slate-500 hover:text-slate-800'}`}>
                        Continuar sin adjuntar comprobante &rarr;
                     </button>
                  )}

                  <button 
                    onClick={handleUpload}
                    disabled={!file || isProcessing || (transactionType === 'Nota de Crédito' && !facturaAsociada.trim()) || (['Boleta', 'Factura', 'Sin Respaldo'].includes(transactionType) && !origenFondos)}
                    className={`mt-6 w-full py-4 rounded-xl font-bold flex items-center justify-center gap-3 text-lg ${(!file || (transactionType === 'Nota de Crédito' && !facturaAsociada.trim()) || (['Boleta', 'Factura', 'Sin Respaldo'].includes(transactionType) && !origenFondos)) ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors shadow-sm font-bold tracking-wide'}`}
                  >
                    {isProcessing ? (
                      <><RefreshCcw className="h-6 w-6 animate-spin" /> Procesando...</>
                    ) : (
                      <><Upload className="h-6 w-6" /> Enviar y Continuar</>
                    )}
                  </button>
                  {error && (
                    <div className="mt-5 w-full p-4 bg-red-50 border border-red-200 text-red-600 text-sm rounded-xl text-center font-medium">
                      <div className="flex items-center justify-center gap-2 mb-3">
                        <ShieldAlert className="h-4 w-4" /> {error}
                      </div>
                      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
                        <button
                          onClick={handleUpload}
                          className="px-5 py-2.5 w-full sm:w-auto bg-red-100 hover:bg-red-200 text-red-700 rounded-lg font-bold text-xs transition-colors flex items-center justify-center gap-2"
                        >
                          <RefreshCcw className="h-4 w-4" /> Reintentar
                        </button>
                        {fallbackData && (
                          <button
                            onClick={() => {
                              setError(null);
                              setReviewData(fallbackData);
                              setFallbackData(null);
                            }}
                            className="px-5 py-2.5 w-full sm:w-auto bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-bold text-xs transition-colors flex items-center justify-center gap-2"
                          >
                          <Edit2 className="h-4 w-4" /> Ingresar Manualmente
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              )
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-lg mx-auto bg-white mt-4">
                <div className="bg-gradient-to-br from-[#38bdf8] to-[#0284c7] p-8 flex flex-col items-center text-white relative overflow-hidden">
                  <div className="absolute -right-10 -top-10 opacity-20">
                    <CheckCircle className="h-48 w-48" />
                  </div>
                  <CheckCircle className="h-16 w-16 mb-4 relative z-10" />
                  <h2 className="text-3xl font-bold mb-2 relative z-10">¡Éxito!</h2>
                  <p className="text-sky-100 font-medium relative z-10 text-center">Transacción registrada en el sistema.</p>
                </div>
                
                <div className="p-8">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 border-b border-slate-100 pb-2">Resumen de Transacción</h3>
                  
                  <div className="space-y-3">
                    <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="h-10 w-10 rounded-lg bg-white shadow-sm flex items-center justify-center">
                        <FileText className="h-5 w-5 text-slate-400" />
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Tipo</p>
                        <p className="text-sm font-semibold text-slate-800">{transactionType}</p>
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
                    Registrar otra transacción <ArrowRight className="h-4 w-4 text-slate-400" />
                  </button>

                  <button 
                    onClick={resetAll}
                    className="mt-3 w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 shadow-sm"
                  >
                    <CheckCircle className="h-4 w-4" /> Volver al Inicio
                  </button>
                </div>
              </div>
            )
          ) : (
            /* TAB HISTORY OR ADMIN CRM */
            <div className="space-y-6">
              
              {/* Dashboard Stats */}
              {activeTab === 'admin' ? (
                <>
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
                    <div className="flex flex-wrap gap-4 mt-3 relative z-10">
                      <p className="text-sm text-sky-600 font-medium flex items-center gap-2">
                        <FileText className="h-4 w-4" /> {totalInvoices} documentos
                      </p>
                      <p className="text-sm text-emerald-600 font-medium flex items-center gap-2">
                        <DollarSign className="h-4 w-4" /> IVA Acum: ${ivaAcumulado.toLocaleString('es-CL')}
                      </p>
                    </div>
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

                {/* Cost Center Stats - Admin */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="h-8 w-8 bg-amber-50 rounded-lg flex items-center justify-center"><Hash className="h-4 w-4 text-amber-500" /></div>
                    <h3 className="font-bold text-slate-700 text-sm">Gasto por Centro de Costo</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {expensesByCostCenter.map(([cc, amount]) => (
                      <div key={cc} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
                        <span className="text-xs font-bold text-slate-600 truncate pr-2">{cc}</span>
                        <span className="text-xs font-bold text-amber-600 whitespace-nowrap">${amount.toLocaleString('es-CL')}</span>
                      </div>
                    ))}
                    {expensesByCostCenter.length === 0 && (
                      <p className="text-xs text-slate-400 col-span-full">Sin datos de centros de costo.</p>
                    )}
                  </div>
                </div>
                </>
              ) : (
                /* 3 CAJAS CONTABLES DEALFLOW v2.4 (MOCKUP JORGE SALAS) */
                <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  
                  {/* CAJA 1: TOTAL A RENDIR (FONDO PRINCIPAL) */}
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div className="h-11 w-11 bg-amber-50 border border-amber-200 text-amber-600 rounded-xl flex items-center justify-center shrink-0">
                          <Wallet className="h-6 w-6" />
                        </div>
                        <div>
                          <p className="text-[11px] font-black text-slate-700 uppercase tracking-wider">Total a Rendir <span className="text-slate-400 font-bold">(Fondo Principal)</span></p>
                          <p className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-0.5">
                            ${finanzas.totalARendir.toLocaleString('es-CL')}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2 pt-3 border-t border-slate-100">
                      <div className="flex items-center justify-between px-3 py-2 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs">
                        <span className="font-bold text-amber-800 uppercase text-[10px] tracking-wider">Pendiente de Aprobación</span>
                        <span className="font-black text-amber-900">${finanzas.pendienteAprobacionCaja.toLocaleString('es-CL')}</span>
                      </div>
                      <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/70 border border-emerald-200/80 rounded-xl text-xs">
                        <span className="font-bold text-emerald-800 uppercase text-[10px] tracking-wider">Saldo Por Rendir</span>
                        <span className={`font-black ${finanzas.saldoPorRendir < 0 ? 'text-rose-700' : 'text-emerald-900'}`}>
                          ${finanzas.saldoPorRendir.toLocaleString('es-CL')}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* CAJA 2: CASA COMERCIAL (BILLETERA VIRTUAL DEVOLUCIONES) */}
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div className="h-11 w-11 bg-sky-50 border border-sky-200 text-sky-600 rounded-xl flex items-center justify-center shrink-0">
                          <CreditCard className="h-6 w-6" />
                        </div>
                        <div>
                          <p className="text-[11px] font-black text-slate-700 uppercase tracking-wider">Casa Comercial <span className="text-slate-400 font-bold">(Billetera Virtual Devoluciones)</span></p>
                          <p className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-0.5">
                            ${finanzas.totalCasaComercial.toLocaleString('es-CL')}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2 pt-3 border-t border-slate-100">
                      <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/70 border border-emerald-200/80 rounded-xl text-xs">
                        <span className="font-bold text-emerald-800 uppercase text-[10px] tracking-wider">Saldo en Casa Comercial</span>
                        <span className="font-black text-emerald-900">${finanzas.saldoEnCasaComercial.toLocaleString('es-CL')}</span>
                      </div>
                      <div className="flex items-center justify-between px-3 py-2 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs">
                        <span className="font-bold text-amber-800 uppercase text-[10px] tracking-wider">Pendiente de Aprobación</span>
                        <span className="font-black text-amber-900">${finanzas.pendienteAprobacionNC.toLocaleString('es-CL')}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* CAJA 3: POR RECUPERAR POR LIQUIDACIÓN (GASTOS SIN RESPALDO) */}
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div className="h-11 w-11 bg-rose-50 border border-rose-200 text-rose-600 rounded-xl flex items-center justify-center shrink-0">
                          <Receipt className="h-6 w-6" />
                        </div>
                        <div>
                          <p className="text-[11px] font-black text-slate-700 uppercase tracking-wider">Por Recuperar por Liquidación</p>
                          <p className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-0.5">
                            ${finanzas.porRecuperarLiquidacion.toLocaleString('es-CL')}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2 pt-3 border-t border-slate-100">
                      <div className="flex items-center justify-between px-3 py-2 bg-rose-50/70 border border-rose-200/80 rounded-xl text-xs">
                        <div className="flex flex-col">
                          <span className="font-bold text-rose-800 uppercase text-[10px] tracking-wider">Fondos Rendidos Sin Respaldo</span>
                          <span className="text-[9px] text-rose-600 font-medium">(Pendiente de depósito de nómina)</span>
                        </div>
                        <span className="font-black text-rose-900">${finanzas.fondosSinRespaldoPendiente.toLocaleString('es-CL')}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Cost Center Stats - History */}
                {expensesByCostCenter.length > 0 && (
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="h-8 w-8 bg-amber-50 rounded-lg flex items-center justify-center"><Hash className="h-4 w-4 text-amber-500" /></div>
                      <h3 className="font-bold text-slate-700 text-sm">Mi Gasto por Centro de Costo</h3>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {expensesByCostCenter.map(([cc, amount]) => (
                        <div key={cc} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
                          <span className="text-xs font-bold text-slate-600 truncate pr-2">{cc}</span>
                          <span className="text-xs font-bold text-amber-600 whitespace-nowrap">${amount.toLocaleString('es-CL')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                </>
              )}

              {/* History Table & Donut Section */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                
                {/* Table Container (3 Cols on Desktop) */}
                <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  
                  {/* Top Bar with Filters */}
                  <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                      <h2 className="text-xl font-bold text-slate-800 flex items-center gap-3">
                        {activeTab === 'admin' ? <><ShieldAlert className="h-5 w-5 text-[#0ea5e9]"/> Auditoría Global</> : <><History className="h-5 w-5 text-slate-400"/> Historial de Rendiciones</>}
                      </h2>
                      <p className="text-sm text-slate-500 mt-1">Explora, filtra y edita los gastos registrados.</p>
                    </div>
                    
                    <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
                      {activeTab === 'admin' && (
                        <HoverDropdown 
                          label="Usuario"
                          value={filterUser}
                          onChange={setFilterUser}
                          options={[{value: '', label: 'Todos'}, ...uniqueUsers.map(u => ({value: u, label: u.split(' ')[0]}))]}
                        />
                      )}
                      <HoverDropdown 
                        label="Departamento"
                        value={filterDept}
                        onChange={setFilterDept}
                        options={[
                          {value: '', label: 'Todos'}, 
                          {value: 'Ventas', label: 'Ventas'},
                          {value: 'Gerencia', label: 'Gerencia'},
                          {value: 'Operaciones', label: 'Operaciones'},
                          {value: 'Administración', label: 'Administración'}
                        ]}
                      />
                      <HoverDropdown 
                        label="Centro Costo"
                        value={filterCostCenter}
                        onChange={setFilterCostCenter}
                        className=""
                        options={[{value: '', label: 'Todos'}, ...uniqueCostCenters.map(cc => ({value: cc, label: cc}))]}
                      />
                      <HoverDropdown 
                        label="Estado"
                        value={filterEstado}
                        onChange={setFilterEstado}
                        options={[{value: '', label: 'Todos'}, ...uniqueEstados.map(e => ({value: e, label: e}))]}
                      />
                      <HoverDropdown 
                        label="Tipo"
                        value={filterTipo}
                        onChange={setFilterTipo}
                        options={[{value: '', label: 'Todos'}, ...uniqueTipos.map(t => ({value: t, label: t}))]}
                      />
                      <div className="flex items-end gap-2">
                        <button 
                          onClick={fetchHistory} 
                          className="h-[42px] px-4 bg-white border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 hover:bg-slate-50 transition-colors flex items-center justify-center"
                          title="Actualizar"
                        >
                          <RefreshCcw className={`h-4 w-4 text-slate-500 ${loadingHistory ? 'animate-spin' : ''}`} />
                        </button>
                        <button 
                          onClick={handleExport}
                          disabled={isExporting}
                          className="h-[42px] px-4 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg outline-none hover:bg-emerald-100 transition-colors flex items-center justify-center gap-2 font-bold text-sm shadow-sm whitespace-nowrap"
                          title="Sincronizar datos actuales a Kame ERP / Google Sheets"
                        >
                          {isExporting ? <RefreshCcw className="h-4 w-4 animate-spin" /> : <HardDriveDownload className="h-4 w-4" />}
                          <span className="hidden sm:inline">Sincronizar Cambios</span>
                        </button>
                        <a 
                          href="https://docs.google.com/spreadsheets/d/13uq1ouzbLlc1efCPaaFpqIxVM_x4e8a93KyVdbEPwUo/edit"
                          target="_blank"
                          rel="noreferrer"
                          className="h-[42px] px-4 bg-sky-50 text-sky-600 border border-sky-200 rounded-lg outline-none hover:bg-sky-100 transition-colors flex items-center justify-center gap-2 font-bold text-sm shadow-sm whitespace-nowrap"
                          title="Abrir Google Sheets en una nueva pestaña"
                        >
                          <FileText className="h-4 w-4" />
                          <span className="hidden sm:inline">Ver Planilla</span>
                        </a>
                      </div>
                    </div>
                  </div>

                  {/* Table Content */}
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
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50/80 text-slate-600">
                            <th className="p-4 text-xs font-bold uppercase tracking-wider">Transacción / Fecha</th>
                            {activeTab === 'admin' && <th className="p-4 text-xs font-bold uppercase tracking-wider">Usuario / Depto</th>}
                            <th className="p-4 text-xs font-bold uppercase tracking-wider">N° Documento</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider">Proveedor / Proyecto</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-center">Estado</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-right">Monto</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-center">Resp.</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-right">Acciones</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredExpenses.map((exp) => (
                            <tr key={exp.id} className="group hover:bg-slate-50/60 transition-colors">
                              <td className="p-4">
                                <div className="flex items-center gap-3">
                                  <div className="h-9 w-9 rounded-lg bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center shrink-0">
                                    <FileText className="h-4.5 w-4.5" />
                                  </div>
                                  <div>
                                    <p className="text-xs font-bold text-slate-800">
                                      {exp.tipo_transaccion || 'Boleta'}
                                      {exp.descripcion && <span className="text-slate-500 font-normal ml-1.5">— {exp.descripcion}</span>}
                                    </p>
                                    <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5 font-medium">
                                      <Calendar className="h-3 w-3" /> {exp.fecha_boleta || exp.fecha_captura?.substring(0,10)}
                                    </p>
                                  </div>
                                </div>
                              </td>
                              {activeTab === 'admin' && (
                                <td className="p-4">
                                  <p className="text-sm font-semibold text-slate-800">{exp.usuario_nombre}</p>
                                  <p className="text-[10px] text-slate-400 uppercase tracking-wider mt-0.5">{exp.departamento}</p>
                                </td>
                              )}
                              <td className="p-4">
                                <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-1 rounded">
                                  {exp.factura_asociada ? `N° Doc: ${exp.factura_asociada}` : '-'}
                                </span>
                              </td>
                              <td className="p-4">
                                <p className="text-sm font-semibold text-slate-700">{exp.rut_proveedor || '-'}</p>
                                <p className="text-xs text-slate-400 mt-0.5">{exp.centro_costo}</p>
                              </td>
                              <td className="p-4 text-center">
                                <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                                  (exp.estado === 'Aprobado' || exp.estado === 'Aprobada') ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                                  (exp.estado === 'Rechazado' || exp.estado === 'Rechazada') ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                                  (exp.estado === 'Anulado' || exp.estado === 'Anulada') ? 'bg-slate-100 text-slate-600 border border-slate-300' :
                                  'bg-amber-100 text-amber-800 border border-amber-200'
                                }`}>
                                  {exp.estado || 'Pendiente de Revisión'}
                                </span>
                              </td>
                              <td className="p-4 text-sm font-black text-slate-900 text-right">
                                ${parseInt(exp.monto_total || 0).toLocaleString('es-CL')}
                              </td>
                              <td className="p-4 text-center">
                                {exp.link_drive ? (
                                  <a href={exp.link_drive} target="_blank" rel="noreferrer" className="inline-flex p-2 bg-slate-50 text-sky-600 hover:bg-sky-50 rounded-lg transition-all border border-slate-200" title="Ver Respaldo en Drive">
                                    <FileText className="h-4 w-4" />
                                  </a>
                                ) : (
                                  <span className="text-xs text-slate-300">-</span>
                                )}
                              </td>
                              <td className="p-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  {isApprover && (exp.estado === 'Pendiente' || exp.estado === 'Pendiente de Revisión') && (
                                    <>
                                      <button onClick={() => handleUpdateStatus(exp.id, 'Aprobado')} className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-all" title="Aprobar Rendición">
                                        <CheckCircle className="h-4 w-4" />
                                      </button>
                                      <button onClick={() => handleUpdateStatus(exp.id, 'Rechazado')} className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-all" title="Rechazar Rendición">
                                        <X className="h-4 w-4" />
                                      </button>
                                    </>
                                  )}
                                  {isApprover && exp.estado !== 'Anulado' && exp.estado !== 'Anulada' && (
                                    <button 
                                      onClick={() => handleUpdateStatus(exp.id, 'Anulado')} 
                                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all" 
                                      title="Anular Transacción"
                                    >
                                      <Ban className="h-5 w-5" />
                                    </button>
                                  )}
                                  <button 
                                    onClick={() => startEdit(exp)}
                                    className="p-1.5 text-slate-400 hover:text-[#38bdf8] hover:bg-sky-50 rounded-lg transition-all"
                                    title="Editar Gasto"
                                  >
                                    <Edit2 className="h-4 w-4" />
                                  </button>
                                  {isApprover && (
                                    <button 
                                      onClick={() => handleDelete(exp.id)}
                                      className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                                      title="Eliminar Gasto"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Table Footer with Monto Total */}
                  <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-3 text-sm">
                    <span className="font-bold text-slate-500 uppercase tracking-wider text-xs">Monto Total</span>
                    <span className="font-black text-slate-900 text-base sm:text-lg">
                      ${finanzas.totalMontoFiltered.toLocaleString('es-CL')}
                    </span>
                  </div>
                </div>

                {/* Right Column: Donut Chart Widget */}
                <div className="lg:col-span-1 space-y-6">
                  <StatusDonutChart 
                    pending={finanzas.countPendiente} 
                    approved={finanzas.countAprobado} 
                    rejected={finanzas.countRechazado} 
                    voided={finanzas.countAnulado} 
                  />
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
                        <input type="text" value={editForm.centro_costo} onChange={e => setEditForm({...editForm, centro_costo: e.target.value.toUpperCase()})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl uppercase" />
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
                        <input type="number" value={editForm.monto_total} onChange={e => setEditForm({...editForm, monto_total: parseFloat(e.target.value) || 0})} className="w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl font-bold text-lg text-[#0284c7]" />
                      </div>

                      {editForm.origen_fondos === 'Fondos Mixtos' && (
                        <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200 space-y-3">
                          <span className="text-xs font-bold text-slate-700 uppercase">Desglose Pago Mixto</span>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[11px] font-bold text-emerald-700 mb-1 uppercase">Monto Caja</label>
                              <input 
                                type="number" 
                                value={editForm.monto_caja} 
                                onChange={e => setEditForm({...editForm, monto_caja: parseFloat(e.target.value) || 0})}
                                className="w-full bg-white border border-emerald-300 rounded-lg px-3 py-2 text-sm font-bold text-emerald-800"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-bold text-purple-700 mb-1 uppercase">Monto NC</label>
                              <input 
                                type="number" 
                                value={editForm.monto_nc} 
                                onChange={e => setEditForm({...editForm, monto_nc: parseFloat(e.target.value) || 0})}
                                className="w-full bg-white border border-purple-300 rounded-lg px-3 py-2 text-sm font-bold text-purple-800"
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Estado</label>
                          {!isApprover && <span className="text-[10px] text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">Solo Lectura (Gerencia/Finanzas)</span>}
                        </div>
                        <select 
                          value={editForm.estado} 
                          onChange={e => setEditForm({...editForm, estado: e.target.value})} 
                          disabled={!isApprover}
                          className={`w-full bg-white border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all p-3 rounded-xl font-bold ${!isApprover ? 'bg-slate-100 text-slate-400 cursor-not-allowed border-slate-200' : 'text-slate-800'}`}
                        >
                          <option value="Pendiente de Revisión">Pendiente de Revisión</option>
                          <option value="Aprobado">Aprobado</option>
                          <option value="Rechazado">Rechazado</option>
                          <option value="Anulado">Anulado</option>
                        </select>
                      </div>
                      <div className="pt-6 flex gap-3">
                        <button onClick={handleEditSubmit} className="bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors shadow-sm font-bold tracking-wide flex-1 py-3.5 rounded-xl text-lg flex justify-center items-center gap-2">
                          Guardar Cambios
                        </button>
                        {isApprover && (
                          <button 
                            onClick={() => {
                              if (window.confirm("¿Estás seguro de anular esta transacción?")) {
                                setEditForm({...editForm, estado: 'Anulado'});
                              }
                            }} 
                            className="bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors font-bold tracking-wide px-4 py-3.5 rounded-xl flex justify-center items-center gap-2"
                            title="Anular Gasto"
                          >
                            <Ban className="h-5 w-5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>

      {/* Global Dialog Modal */}
      {dialog.isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden transform transition-all animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                {dialog.type === 'error' ? (
                  <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  </div>
                ) : dialog.type === 'success' ? (
                  <div className="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                    <CheckCircle className="h-5 w-5 text-emerald-600" />
                  </div>
                ) : (
                  <div className="h-10 w-10 rounded-full bg-sky-100 flex items-center justify-center shrink-0">
                    <HelpCircle className="h-5 w-5 text-sky-600" />
                  </div>
                )}
                <h3 className="font-bold text-slate-800 text-lg">{dialog.title}</h3>
              </div>
              <p className="text-slate-600 text-[13px] whitespace-pre-line leading-relaxed">{dialog.message}</p>
            </div>
            <div className="bg-slate-50 px-6 py-4 flex justify-end gap-3 border-t border-slate-100">
              {dialog.type === 'confirm' && (
                <button 
                  onClick={() => setDialog({ ...dialog, isOpen: false })}
                  className="px-4 py-2 text-sm font-bold text-slate-500 hover:bg-slate-200 bg-slate-200/50 rounded-lg transition-colors outline-none"
                >
                  Cancelar
                </button>
              )}
              <button 
                onClick={() => {
                  if (dialog.onConfirm) dialog.onConfirm();
                  else setDialog({ ...dialog, isOpen: false });
                }}
                className={`px-4 py-2 text-sm font-bold text-white rounded-lg transition-colors outline-none ${
                  dialog.type === 'error' ? 'bg-red-500 hover:bg-red-600' :
                  dialog.type === 'success' ? 'bg-emerald-500 hover:bg-emerald-600' :
                  'bg-sky-500 hover:bg-sky-600'
                }`}
              >
                {dialog.type === 'confirm' ? 'Aceptar' : 'Entendido'}
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
  );
}

export default App;
