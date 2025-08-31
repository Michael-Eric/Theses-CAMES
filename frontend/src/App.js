import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import './App.css';

// Import Shadcn UI components
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Separator } from './components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './components/ui/dropdown-menu';

// Import Lucide React icons
import { Search, BookOpen, Users, University, Star, Eye, Download, Calendar, MapPin, Award, ExternalLink, ShoppingCart, Filter, MoreVertical, Flag, UserCheck } from 'lucide-react';

// Import Auth components
import { AuthProvider, UserMenu, ThesisClaimModal, ThesisReportModal } from './components/Auth';

// Import Language Switcher
import LanguageSwitcher from './components/LanguageSwitcher';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Header Component
const Header = ({ onSearch, searchQuery, setSearchQuery }) => {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Thèses CAMES</h1>
              <p className="text-sm text-gray-500">Plateforme de thèses académiques</p>
            </div>
          </div>
          
          <div className="flex-1 max-w-2xl mx-8">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Rechercher par titre, auteur, mots-clés..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    onSearch();
                  }
                }}
                className="pl-10 pr-4 py-2 w-full"
              />
              <Button
                onClick={onSearch}
                className="absolute right-1 top-1 h-8 px-3"
                size="sm"
              >
                Rechercher
              </Button>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <Button variant="outline" size="sm">
              <Users className="w-4 h-4 mr-2" />
              Palmarès
            </Button>
            <Button variant="outline" size="sm">
              <University className="w-4 h-4 mr-2" />
              Universités
            </Button>
            <UserMenu />
          </div>
        </div>
      </div>
    </header>
  );
};

// Thesis Card Component
const ThesisCard = ({ thesis, onClick }) => {
  const getAccessBadge = () => {
    if (thesis.access_type === 'open') {
      return <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-100">Accès libre</Badge>;
    } else {
      return <Badge variant="secondary" className="bg-orange-100 text-orange-800 hover:bg-orange-100">Payant</Badge>;
    }
  };

  const getStars = (count) => {
    let stars = 0;
    if (count >= 50) stars = 5;
    else if (count >= 25) stars = 4;
    else if (count >= 10) stars = 3;
    else if (count >= 5) stars = 2;
    else if (count >= 1) stars = 1;
    
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-3 h-3 ${i < stars ? 'text-yellow-400 fill-current' : 'text-gray-300'}`}
      />
    ));
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-200 cursor-pointer h-full" onClick={() => onClick(thesis)}>
      <CardContent className="p-6">
        <div className="space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex-1 pr-4">
              <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 mb-2">
                {thesis.title}
              </h3>
              <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                {thesis.abstract}
              </p>
            </div>
            {thesis.thumbnail && (
              <img
                src={thesis.thumbnail}
                alt="Thesis thumbnail"
                className="w-16 h-16 object-cover rounded-lg flex-shrink-0"
              />
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="font-medium">{thesis.author_name}</span>
              <Separator orientation="vertical" className="h-4" />
              <span>{thesis.university}</span>
            </div>
            
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <div className="flex items-center">
                <MapPin className="w-3 h-3 mr-1" />
                {thesis.country}
              </div>
              <div className="flex items-center">
                <Calendar className="w-3 h-3 mr-1" />
                {thesis.defense_date}
              </div>
              <Badge variant="outline" className="text-xs">
                {thesis.discipline}
              </Badge>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <div className="flex items-center space-x-4">
              {getAccessBadge()}
              <div className="flex items-center space-x-1">
                {getStars(thesis.site_citations_count)}
                <span className="text-xs text-gray-500 ml-1">
                  ({thesis.site_citations_count})
                </span>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 text-xs text-gray-500">
              <div className="flex items-center">
                <Eye className="w-3 h-3 mr-1" />
                {thesis.views_count}
              </div>
              <div className="flex items-center">
                <Download className="w-3 h-3 mr-1" />
                {thesis.downloads_count}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Thesis Detail Modal Component
const ThesisDetailModal = ({ thesis, onClose, onPurchase }) => {
  const [showClaimModal, setShowClaimModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);

  if (!thesis) return null;

  const getStars = (count) => {
    let stars = 0;
    if (count >= 200) stars = 5;
    else if (count >= 100) stars = 4;
    else if (count >= 50) stars = 3;
    else if (count >= 20) stars = 2;
    else if (count >= 5) stars = 1;
    
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < stars ? 'text-yellow-400 fill-current' : 'text-gray-300'}`}
      />
    ));
  };

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex justify-between items-start mb-6">
              <h2 className="text-2xl font-bold text-gray-900 pr-4">{thesis.title}</h2>
              <div className="flex items-center space-x-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => setShowClaimModal(true)}>
                      <UserCheck className="w-4 h-4 mr-2" />
                      Revendiquer cette thèse
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setShowReportModal(true)}>
                      <Flag className="w-4 h-4 mr-2" />
                      Signaler un problème
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button variant="outline" size="sm" onClick={onClose}>
                  ✕
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2 space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-3">Résumé</h3>
                  <p className="text-gray-700 leading-relaxed">
                    {thesis.abstract}
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-3">Mots-clés</h3>
                  <div className="flex flex-wrap gap-2">
                    {thesis.keywords.map((keyword, index) => (
                      <Badge key={index} variant="secondary">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-3">Statistiques</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <Eye className="w-6 h-6 mx-auto mb-1 text-blue-600" />
                      <div className="font-semibold">{thesis.views_count}</div>
                      <div className="text-xs text-gray-500">Vues</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <Download className="w-6 h-6 mx-auto mb-1 text-green-600" />
                      <div className="font-semibold">{thesis.downloads_count}</div>
                      <div className="text-xs text-gray-500">Téléchargements</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <Award className="w-6 h-6 mx-auto mb-1 text-yellow-600" />
                      <div className="font-semibold">{thesis.site_citations_count}</div>
                      <div className="text-xs text-gray-500">Citations</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="flex justify-center mb-1">
                        {getStars(thesis.site_citations_count)}
                      </div>
                      <div className="text-xs text-gray-500">Évaluation</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Informations</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <h4 className="font-medium text-gray-900">Auteur</h4>
                      <p className="text-gray-600">{thesis.author_name}</p>
                      {thesis.author_orcid && (
                        <p className="text-xs text-gray-500">ORCID: {thesis.author_orcid}</p>
                      )}
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900">Directeurs de thèse</h4>
                      {thesis.supervisor_names.map((supervisor, index) => (
                        <p key={index} className="text-gray-600">{supervisor}</p>
                      ))}
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900">Université</h4>
                      <p className="text-gray-600">{thesis.university}</p>
                      <p className="text-sm text-gray-500">{thesis.country}</p>
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900">Discipline</h4>
                      <p className="text-gray-600">{thesis.discipline}</p>
                      {thesis.sub_discipline && (
                        <p className="text-sm text-gray-500">{thesis.sub_discipline}</p>
                      )}
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900">Soutenance</h4>
                      <p className="text-gray-600">{thesis.defense_date}</p>
                    </div>

                    {thesis.pages && (
                      <div>
                        <h4 className="font-medium text-gray-900">Pages</h4>
                        <p className="text-gray-600">{thesis.pages} pages</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Accès au document</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {thesis.access_type === 'open' ? (
                      <div className="space-y-3">
                        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                          Accès libre
                        </Badge>
                        <div className="space-y-2">
                          {thesis.url_open_access && (
                            <Button className="w-full" size="sm">
                              <ExternalLink className="w-4 h-4 mr-2" />
                              Consulter en ligne
                            </Button>
                          )}
                          <Button variant="outline" className="w-full" size="sm">
                            <Download className="w-4 h-4 mr-2" />
                            Télécharger
                          </Button>
                        </div>
                        {thesis.source_url && (
                          <div className="pt-2 border-t">
                            <p className="text-xs text-gray-500 mb-1">Source:</p>
                            <Button variant="link" className="h-auto p-0 text-xs">
                              {thesis.source_repo} - Lien original
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <Badge className="bg-orange-100 text-orange-800 hover:bg-orange-100">
                          Accès payant
                        </Badge>
                        <Button 
                          className="w-full bg-orange-600 hover:bg-orange-700" 
                          onClick={() => onPurchase(thesis)}
                        >
                          <ShoppingCart className="w-4 h-4 mr-2" />
                          Acheter l'accès
                        </Button>
                        <p className="text-xs text-gray-500 text-center">
                          Paiement sécurisé • Accès immédiat
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ThesisClaimModal 
        isOpen={showClaimModal}
        onClose={() => setShowClaimModal(false)}
        thesis={thesis}
      />

      <ThesisReportModal 
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        thesis={thesis}
      />
    </>
  );
};

// Filter Panel Component
const FilterPanel = ({ filters, onFilterChange, stats }) => {
  return (
    <Card className="p-4">
      <div className="flex items-center mb-4">
        <Filter className="w-4 h-4 mr-2" />
        <h3 className="font-semibold">Filtres</h3>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Pays</label>
          <Select value={filters.country || 'all'} onValueChange={(value) => onFilterChange('country', value === 'all' ? null : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Tous les pays" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les pays</SelectItem>
              {stats?.top_countries?.map((country) => (
                <SelectItem key={country.name} value={country.name}>
                  {country.name} ({country.count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Discipline</label>
          <Select value={filters.discipline || 'all'} onValueChange={(value) => onFilterChange('discipline', value === 'all' ? null : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Toutes disciplines" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes disciplines</SelectItem>
              {stats?.top_disciplines?.map((discipline) => (
                <SelectItem key={discipline.name} value={discipline.name}>
                  {discipline.name} ({discipline.count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Université</label>
          <Select value={filters.university || 'all'} onValueChange={(value) => onFilterChange('university', value === 'all' ? null : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Toutes universités" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes universités</SelectItem>
              {stats?.top_universities?.map((university) => (
                <SelectItem key={university.name} value={university.name}>
                  {university.name} ({university.count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Type d'accès</label>
          <Select value={filters.access_type || 'all'} onValueChange={(value) => onFilterChange('access_type', value === 'all' ? null : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Tous types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous types</SelectItem>
              <SelectItem value="open">Accès libre</SelectItem>
              <SelectItem value="paywalled">Payant</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Année</label>
          <Select value={filters.year || 'all'} onValueChange={(value) => onFilterChange('year', value === 'all' ? null : value)}>
            <SelectTrigger>
              <SelectValue placeholder="Toutes années" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes années</SelectItem>
              <SelectItem value="2023">2023</SelectItem>
              <SelectItem value="2022">2022</SelectItem>
              <SelectItem value="2021">2021</SelectItem>
              <SelectItem value="2020">2020</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </Card>
  );
};

// Rankings Component
const Rankings = () => {
  const [authorRankings, setAuthorRankings] = useState([]);
  const [universityRankings, setUniversityRankings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRankings();
  }, []);

  const fetchRankings = async () => {
    setLoading(true);
    try {
      const [authorsRes, universitiesRes] = await Promise.all([
        axios.get(`${API}/rankings/authors?limit=20`),
        axios.get(`${API}/rankings/universities?limit=20`)
      ]);
      
      setAuthorRankings(authorsRes.data);
      setUniversityRankings(universitiesRes.data);
    } catch (error) {
      console.error('Error fetching rankings:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStars = (count) => {
    let stars = 0;
    if (count >= 200) stars = 5;
    else if (count >= 100) stars = 4;
    else if (count >= 50) stars = 3;
    else if (count >= 20) stars = 2;
    else if (count >= 5) stars = 1;
    
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < stars ? 'text-yellow-400 fill-current' : 'text-gray-300'}`}
      />
    ));
  };

  if (loading) {
    return <div className="text-center py-8">Chargement des palmarès...</div>;
  }

  return (
    <div className="space-y-8">
      <Tabs defaultValue="authors" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="authors">Auteurs les plus consultés cette semaine</TabsTrigger>
          <TabsTrigger value="universities">Universités les plus consultées</TabsTrigger>
        </TabsList>
        
        <TabsContent value="authors" className="space-y-4">
          <div className="grid gap-4">
            {authorRankings.map((author, index) => (
              <Card key={index}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                        {index + 1}
                      </div>
                      <div>
                        <h3 className="font-semibold">{author.author_name}</h3>
                        <p className="text-sm text-gray-600">
                          {author.theses_count} thèse{author.theses_count > 1 ? 's' : ''} • {author.weekly_views} consultation{author.weekly_views > 1 ? 's' : ''} cette semaine
                        </p>
                        <p className="text-xs text-gray-500">
                          {author.total_views} consultations au total
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="flex">
                        {getStars(author.weekly_views)}
                      </div>
                      <Badge variant="outline">
                        {author.disciplines[0]}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
        
        <TabsContent value="universities" className="space-y-4">
          <div className="grid gap-4">
            {universityRankings.map((university, index) => (
              <Card key={index}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                        {index + 1}
                      </div>
                      <div>
                        <h3 className="font-semibold">{university.university_name}</h3>
                        <p className="text-sm text-gray-600">
                          {university.country} • {university.weekly_views} consultations cette semaine
                        </p>
                        <p className="text-xs text-gray-500">
                          {university.theses_count} thèse{university.theses_count > 1 ? 's' : ''} • {university.total_views} vues totales
                        </p>
                        {university.top_authors && university.top_authors.length > 0 && (
                          <p className="text-xs text-gray-400 mt-1">
                            Auteurs: {university.top_authors.slice(0, 2).join(', ')}
                            {university.top_authors.length > 2 && ` +${university.top_authors.length - 2} autres`}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {university.disciplines.slice(0, 2).map((discipline, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {discipline}
                        </Badge>
                      ))}
                      {university.disciplines.length > 2 && (
                        <Badge variant="outline" className="text-xs">
                          +{university.disciplines.length - 2}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Purchase Success Component
const PurchaseSuccess = () => {
  const [paymentStatus, setPaymentStatus] = useState('checking');
  const [thesisId, setThesisId] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionIdParam = urlParams.get('session_id');
    const thesisIdParam = urlParams.get('thesis_id');
    
    if (sessionIdParam && thesisIdParam) {
      setSessionId(sessionIdParam);
      setThesisId(thesisIdParam);
      pollPaymentStatus(sessionIdParam);
    } else {
      setPaymentStatus('error');
    }
  }, []);

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 10;
    const pollInterval = 2000; // 2 seconds

    if (attempts >= maxAttempts) {
      setPaymentStatus('timeout');
      return;
    }

    try {
      const response = await axios.get(`${API}/checkout/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        setPaymentStatus('success');
        return;
      } else if (response.data.status === 'expired') {
        setPaymentStatus('expired');
        return;
      }

      // If payment is still pending, continue polling
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setPaymentStatus('error');
    }
  };

  const renderContent = () => {
    switch (paymentStatus) {
      case 'checking':
        return (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <h2 className="text-2xl font-semibold mb-2">Vérification du paiement...</h2>
            <p className="text-gray-600">Veuillez patienter pendant que nous confirmons votre paiement.</p>
          </div>
        );
      
      case 'success':
        return (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-green-800 mb-2">Paiement réussi !</h2>
            <p className="text-gray-600 mb-6">Merci pour votre achat. Vous avez maintenant accès à cette thèse.</p>
            <div className="space-y-3">
              <Button 
                onClick={() => window.location.href = `/?thesis=${thesisId}`}
                className="bg-green-600 hover:bg-green-700"
              >
                Consulter la thèse
              </Button>
              <br />
              <Button 
                variant="outline"
                onClick={() => window.location.href = '/'}
              >
                Retour à l'accueil
              </Button>
            </div>
          </div>
        );
      
      case 'expired':
        return (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-orange-800 mb-2">Session expirée</h2>
            <p className="text-gray-600 mb-6">Votre session de paiement a expiré. Veuillez réessayer.</p>
            <Button 
              variant="outline"
              onClick={() => window.location.href = '/'}
            >
              Retour à l'accueil
            </Button>
          </div>
        );
      
      case 'timeout':
        return (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-yellow-800 mb-2">Vérification en cours</h2>
            <p className="text-gray-600 mb-6">La vérification du paiement prend plus de temps que prévu. Vérifiez votre email pour la confirmation.</p>
            <Button 
              variant="outline"
              onClick={() => window.location.href = '/'}
            >
              Retour à l'accueil
            </Button>
          </div>
        );
      
      default:
        return (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-red-800 mb-2">Erreur</h2>
            <p className="text-gray-600 mb-6">Une erreur est survenue lors de la vérification du paiement.</p>
            <Button 
              variant="outline"
              onClick={() => window.location.href = '/'}
            >
              Retour à l'accueil
            </Button>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        {renderContent()}
      </div>
    </div>
  );
};

// Main Home Component
const Home = () => {
  const [theses, setTheses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedThesis, setSelectedThesis] = useState(null);
  const [filters, setFilters] = useState({});
  const [stats, setStats] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showRankings, setShowRankings] = useState(false);

  useEffect(() => {
    fetchTheses();
    fetchStats();
  }, [filters, currentPage]);

  const fetchTheses = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (filters.country) params.append('country', filters.country);
      if (filters.discipline) params.append('discipline', filters.discipline);
      if (filters.access_type) params.append('access_type', filters.access_type);
      if (filters.year) params.append('year', filters.year);
      params.append('page', currentPage.toString());
      params.append('limit', '12');

      const response = await axios.get(`${API}/theses?${params.toString()}`);
      setTheses(response.data.results);
      setTotalPages(response.data.total_pages);
    } catch (error) {
      console.error('Error fetching theses:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleSearch = () => {
    setCurrentPage(1);
    fetchTheses();
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const handleThesisClick = (thesis) => {
    setSelectedThesis(thesis);
  };

  const handlePurchase = async (thesis) => {
    try {
      const originUrl = window.location.origin;
      
      const response = await axios.post(`${API}/checkout/session`, {
        thesis_id: thesis.id,
        origin_url: originUrl
      });
      
      if (response.data.url) {
        // Redirect to Stripe checkout
        window.location.href = response.data.url;
      } else {
        alert('Erreur lors de la création de la session de paiement');
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
      if (error.response?.status === 400) {
        alert(error.response.data.detail || 'Cette thèse est déjà accessible gratuitement');
      } else {
        alert('Erreur lors de l\'initialisation du paiement. Veuillez réessayer.');
      }
    }
  };

  if (showRankings) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header 
          onSearch={handleSearch}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Palmarès</h1>
            <Button onClick={() => setShowRankings(false)} variant="outline">
              Retour à la recherche
            </Button>
          </div>
          <Rankings />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        onSearch={handleSearch}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />
      
      {/* Hero Stats */}
      {stats && (
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.total_theses}</div>
                <div className="text-sm text-gray-500">Thèses totales</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.open_access}</div>
                <div className="text-sm text-gray-500">Accès libre</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{stats.paywalled}</div>
                <div className="text-sm text-gray-500">Payantes</div>
              </div>
              <div className="text-center">
                <Button onClick={() => setShowRankings(true)} variant="outline" size="sm">
                  <Award className="w-4 h-4 mr-2" />
                  Voir palmarès
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            <FilterPanel 
              filters={filters}
              onFilterChange={handleFilterChange}
              stats={stats}
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-2 text-gray-600">Chargement des thèses...</p>
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    {searchQuery ? `Résultats pour "${searchQuery}"` : 'Toutes les thèses'}
                  </h2>
                  <p className="text-sm text-gray-500">
                    Page {currentPage} sur {totalPages}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  {theses.map((thesis) => (
                    <ThesisCard
                      key={thesis.id}
                      thesis={thesis}
                      onClick={handleThesisClick}
                    />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex justify-center space-x-2">
                    <Button
                      variant="outline"
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    >
                      Précédent
                    </Button>
                    <Button
                      variant="outline"
                      disabled={currentPage === totalPages}
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    >
                      Suivant
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Thesis Detail Modal */}
      {selectedThesis && (
        <ThesisDetailModal
          thesis={selectedThesis}
          onClose={() => setSelectedThesis(null)}
          onPurchase={handlePurchase}
        />
      )}
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/purchase-success" element={<PurchaseSuccess />} />
          </Routes>
        </BrowserRouter>
      </div>
    </AuthProvider>
  );
}

export default App;