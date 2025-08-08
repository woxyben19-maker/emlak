import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { Search, Download, FileText, Users, MapPin, Calendar, AlertCircle, CheckCircle, Clock } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [url, setUrl] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [scrapingResults, setScrapingResults] = useState([]);
  const [currentResult, setCurrentResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testStatus, setTestStatus] = useState(null);

  const months = [
    { value: 1, label: 'Ocak' },
    { value: 2, label: 'Şubat' },
    { value: 3, label: 'Mart' },
    { value: 4, label: 'Nisan' },
    { value: 5, label: 'Mayıs' },
    { value: 6, label: 'Haziran' },
    { value: 7, label: 'Temmuz' },
    { value: 8, label: 'Ağustos' },
    { value: 9, label: 'Eylül' },
    { value: 10, label: 'Ekim' },
    { value: 11, label: 'Kasım' },
    { value: 12, label: 'Aralık' }
  ];

  // Test API connection on component mount
  useEffect(() => {
    testGeminiConnection();
    loadResults();
  }, []);

  const testGeminiConnection = async () => {
    try {
      const response = await axios.post(`${API}/test-gemini`);
      setTestStatus(response.data.status === 'success' ? 'success' : 'error');
    } catch (error) {
      console.error('Gemini test failed:', error);
      setTestStatus('error');
    }
  };

  const loadResults = async () => {
    try {
      const response = await axios.get(`${API}/results`);
      setScrapingResults(response.data);
    } catch (error) {
      console.error('Failed to load results:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) {
      alert('Lütfen Sahibinden.com linkini girin!');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/scrape`, {
        url: url.trim(),
        month: selectedMonth,
        year: 2025
      });
      
      setCurrentResult(response.data);
      await loadResults();
      
      // Poll for updates
      const pollInterval = setInterval(async () => {
        try {
          const updatedResult = await axios.get(`${API}/results/${response.data.id}`);
          setCurrentResult(updatedResult.data);
          
          if (updatedResult.data.status === 'completed' || updatedResult.data.status === 'error') {
            clearInterval(pollInterval);
            setLoading(false);
            await loadResults();
          }
        } catch (error) {
          console.error('Polling error:', error);
          clearInterval(pollInterval);
          setLoading(false);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Scraping error:', error);
      setLoading(false);
      alert('Hata oluştu: ' + (error.response?.data?.detail || error.message));
    }
  };

  const downloadExcel = async (resultId) => {
    try {
      const response = await axios.get(`${API}/export/excel/${resultId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `emlak_listesi_${resultId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Excel export error:', error);
      alert('Excel indirme hatası!');
    }
  };

  const downloadPDF = async (resultId) => {
    try {
      const response = await axios.get(`${API}/export/pdf/${resultId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `emlak_listesi_${resultId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF export error:', error);
      alert('PDF indirme hatası!');
    }
  };

  const StatusIndicator = () => {
    if (testStatus === 'success') {
      return (
        <div className="flex items-center text-green-600 text-sm mb-4">
          <CheckCircle className="w-4 h-4 mr-2" />
          AI Bağlantısı Aktif - %100 Doğruluk Modu
        </div>
      );
    } else if (testStatus === 'api_disabled') {
      return (
        <div className="flex items-center text-yellow-600 text-sm mb-4">
          <AlertCircle className="w-4 h-4 mr-2" />
          HTML Parsing Modu - AI API Etkinleştirilebilir
        </div>
      );
    } else if (testStatus === 'error') {
      return (
        <div className="flex items-center text-orange-600 text-sm mb-4">
          <AlertCircle className="w-4 h-4 mr-2" />
          HTML Parsing Modu - AI Olmadan Çalışıyor
        </div>
      );
    }
    return (
      <div className="flex items-center text-yellow-600 text-sm mb-4">
        <Clock className="w-4 h-4 mr-2" />
        AI Bağlantısı Test Ediliyor...
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            Sahibinden.com Emlak Veri Çıkarıcı
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            AI destekli teknoloji ile emlak ilanlarından detaylı bilgileri otomatik olarak çıkartın ve modern listeler halinde görüntüleyin.
          </p>
          <StatusIndicator />
        </div>

        {/* Main Form */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  <MapPin className="inline w-4 h-4 mr-2" />
                  Sahibinden.com Kiralık/Satılık Kategori Linki
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.sahibinden.com/satilik-daire/istanbul"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  <Calendar className="inline w-4 h-4 mr-2" />
                  Ay Seçimi
                </label>
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(Number(e.target.value))}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  disabled={loading}
                >
                  {months.map(month => (
                    <option key={month.value} value={month.value}>
                      {month.label} 2025
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-4 px-6 rounded-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                <Search className="w-5 h-5" />
                <span>{loading ? 'İlanlar İşleniyor...' : 'İlanları Çıkart ve Listele'}</span>
              </button>
            </form>
          </div>

          {/* Current Processing Status */}
          {currentResult && loading && (
            <div className="bg-white rounded-2xl shadow-xl p-6 mb-8">
              <h3 className="text-xl font-bold text-gray-800 mb-4">İşlem Durumu</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Toplam İlan:</span>
                  <span className="font-semibold">{currentResult.total_listings}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">İşlenen İlan:</span>
                  <span className="font-semibold">{currentResult.processed_listings}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Durum:</span>
                  <span className={`font-semibold ${
                    currentResult.status === 'completed' ? 'text-green-600' :
                    currentResult.status === 'error' ? 'text-red-600' :
                    'text-blue-600'
                  }`}>
                    {currentResult.status === 'processing' ? 'İşleniyor' :
                     currentResult.status === 'scraping' ? 'İlanlar Toplanıyor' :
                     currentResult.status === 'processing_ai' ? 'AI ile Analiz Ediliyor' :
                     currentResult.status === 'completed' ? 'Tamamlandı' :
                     currentResult.status === 'error' ? 'Hata' : currentResult.status}
                  </span>
                </div>
                {currentResult.total_listings > 0 && (
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${(currentResult.processed_listings / currentResult.total_listings) * 100}%` }}
                    ></div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Results List */}
          {scrapingResults.length > 0 && (
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">
                <Users className="inline w-6 h-6 mr-2" />
                İşlem Sonuçları
              </h2>

              <div className="space-y-4">
                {scrapingResults.map((result, index) => (
                  <div key={result.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-all">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-semibold text-gray-800 mb-2">
                          İşlem #{index + 1} - {months.find(m => m.value === result.month)?.label} 2025
                        </h3>
                        <p className="text-sm text-gray-600 break-all">{result.url}</p>
                      </div>
                      <div className="text-right">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          result.status === 'completed' ? 'bg-green-100 text-green-800' :
                          result.status === 'error' ? 'bg-red-100 text-red-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {result.status === 'completed' ? 'Tamamlandı' :
                           result.status === 'error' ? 'Hata' :
                           'İşleniyor'}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">{result.total_listings}</div>
                        <div className="text-xs text-gray-500">Toplam İlan</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{result.processed_listings}</div>
                        <div className="text-xs text-gray-500">İşlenen</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">{result.listings?.length || 0}</div>
                        <div className="text-xs text-gray-500">Başarılı</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-600">
                          {new Date(result.created_date).toLocaleDateString('tr-TR')}
                        </div>
                        <div className="text-xs text-gray-500">Tarih</div>
                      </div>
                    </div>

                    {result.status === 'completed' && result.listings?.length > 0 && (
                      <>
                        <div className="flex space-x-4 mb-4">
                          <button
                            onClick={() => downloadExcel(result.id)}
                            className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-all transform hover:scale-105"
                          >
                            <Download className="w-4 h-4" />
                            <span>Excel İndir</span>
                          </button>
                          <button
                            onClick={() => downloadPDF(result.id)}
                            className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-all transform hover:scale-105"
                          >
                            <FileText className="w-4 h-4" />
                            <span>PDF İndir</span>
                          </button>
                        </div>

                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="bg-gray-50">
                                <th className="px-4 py-2 text-left">İlan Sahibi</th>
                                <th className="px-4 py-2 text-left">Telefon</th>
                                <th className="px-4 py-2 text-left">Oda Sayısı</th>
                                <th className="px-4 py-2 text-left">Net m²</th>
                                <th className="px-4 py-2 text-left">Site İçi</th>
                                <th className="px-4 py-2 text-left">Isıtma</th>
                                <th className="px-4 py-2 text-left">Otopark</th>
                                <th className="px-4 py-2 text-left">Krediye Uygun</th>
                                <th className="px-4 py-2 text-left">Fiyat</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.listings.slice(0, 5).map((listing, i) => (
                                <tr key={i} className="border-t">
                                  <td className="px-4 py-2">{listing.owner_name || '-'}</td>
                                  <td className="px-4 py-2">{listing.contact_number || '-'}</td>
                                  <td className="px-4 py-2">{listing.room_count || '-'}</td>
                                  <td className="px-4 py-2">{listing.net_area || '-'}</td>
                                  <td className="px-4 py-2">
                                    {listing.is_in_complex && listing.complex_name ? 
                                      `Evet (${listing.complex_name})` : 
                                      listing.is_in_complex || '-'
                                    }
                                  </td>
                                  <td className="px-4 py-2">{listing.heating_type || '-'}</td>
                                  <td className="px-4 py-2">{listing.parking_type || '-'}</td>
                                  <td className="px-4 py-2">{listing.credit_suitable || '-'}</td>
                                  <td className="px-4 py-2">{listing.price || '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {result.listings.length > 5 && (
                            <p className="text-center text-gray-500 py-4">
                              ... ve {result.listings.length - 5} ilan daha (Excel/PDF'de tüm liste)
                            </p>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;