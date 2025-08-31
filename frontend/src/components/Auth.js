import React, { useState, useContext, createContext, useEffect } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';
import { Alert, AlertDescription } from './ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { User, LogIn, LogOut, Settings, BookOpen, Award, AlertTriangle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Configure axios to include token in requests
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check authentication on app start
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`);
          setUser(response.data);
        } catch (error) {
          // Token is invalid, clear it
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password
      });

      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);

      // Get user info
      const userResponse = await axios.get(`${API}/auth/me`);
      setUser(userResponse.data);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      return { success: true, user: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Registration failed'
      };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await axios.put(`${API}/auth/me`, profileData);
      setUser(response.data);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Profile update failed'
      };
    }
  };

  const claimThesis = async (thesisId, claimType, message) => {
    try {
      const response = await axios.post(`${API}/auth/claim-thesis`, {
        thesis_id: thesisId,
        claim_type: claimType,
        message
      });
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Claim submission failed'
      };
    }
  };

  const reportThesis = async (thesisId, reportType, description) => {
    try {
      const response = await axios.post(`${API}/auth/report-thesis`, {
        thesis_id: thesisId,
        report_type: reportType,
        description
      });
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Report submission failed'
      };
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    updateProfile,
    claimThesis,
    reportThesis,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Login/Register Modal
export const AuthModal = ({ isOpen, onClose, defaultTab = 'login' }) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const { login, register } = useAuth();

  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  });

  const [registerData, setRegisterData] = useState({
    email: '',
    name: '',
    password: '',
    confirmPassword: '',
    role: 'visitor',
    institution: '',
    country: '',
    orcid: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(loginData.email, loginData.password);
    
    if (result.success) {
      setSuccess('Connexion réussie !');
      setTimeout(() => {
        onClose();
        window.location.reload(); // Refresh to update UI
      }, 1000);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (registerData.password !== registerData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      setLoading(false);
      return;
    }

    const result = await register({
      email: registerData.email,
      name: registerData.name,
      password: registerData.password,
      role: registerData.role,
      institution: registerData.institution || undefined,
      country: registerData.country || undefined,
      orcid: registerData.orcid || undefined
    });

    if (result.success) {
      setSuccess('Inscription réussie ! Vous pouvez maintenant vous connecter.');
      setActiveTab('login');
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Authentification</DialogTitle>
          <DialogDescription>
            Connectez-vous ou créez un compte pour accéder aux fonctionnalités avancées.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="login">Connexion</TabsTrigger>
            <TabsTrigger value="register">Inscription</TabsTrigger>
          </TabsList>

          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert>
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          <TabsContent value="login">
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={loginData.email}
                  onChange={(e) => setLoginData(prev => ({ ...prev, email: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="password">Mot de passe</Label>
                <Input
                  id="password"
                  type="password"
                  value={loginData.password}
                  onChange={(e) => setLoginData(prev => ({ ...prev, password: e.target.value }))}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="register">
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <Label htmlFor="reg-name">Nom complet</Label>
                <Input
                  id="reg-name"
                  value={registerData.name}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="reg-email">Email</Label>
                <Input
                  id="reg-email"
                  type="email"
                  value={registerData.email}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, email: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="reg-password">Mot de passe</Label>
                <Input
                  id="reg-password"
                  type="password"
                  value={registerData.password}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, password: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="reg-confirm">Confirmer le mot de passe</Label>
                <Input
                  id="reg-confirm"
                  type="password"
                  value={registerData.confirmPassword}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="reg-role">Type de profil</Label>
                <Select value={registerData.role} onValueChange={(value) => setRegisterData(prev => ({ ...prev, role: value }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="visitor">Visiteur</SelectItem>
                    <SelectItem value="author">Auteur/Doctorant</SelectItem>
                    <SelectItem value="university">Université</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="reg-institution">Institution (optionnel)</Label>
                <Input
                  id="reg-institution"
                  value={registerData.institution}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, institution: e.target.value }))}
                />
              </div>
              <div>
                <Label htmlFor="reg-country">Pays (optionnel)</Label>
                <Input
                  id="reg-country"
                  value={registerData.country}
                  onChange={(e) => setRegisterData(prev => ({ ...prev, country: e.target.value }))}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Inscription...' : "S'inscrire"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

// User Menu Component
export const UserMenu = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);

  if (!isAuthenticated) {
    return (
      <>
        <Button variant="outline" onClick={() => setShowAuthModal(true)}>
          <LogIn className="w-4 h-4 mr-2" />
          Connexion
        </Button>
        <AuthModal 
          isOpen={showAuthModal} 
          onClose={() => setShowAuthModal(false)} 
        />
      </>
    );
  }

  return (
    <>
      <div className="flex items-center space-x-4">
        <Button variant="ghost" onClick={() => setShowProfileModal(true)}>
          <User className="w-4 h-4 mr-2" />
          {user.name}
        </Button>
        <Button variant="outline" onClick={logout}>
          <LogOut className="w-4 h-4 mr-2" />
          Déconnexion
        </Button>
      </div>
      
      <ProfileModal 
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
      />
    </>
  );
};

// Profile Modal Component
export const ProfileModal = ({ isOpen, onClose }) => {
  const { user, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    institution: user?.institution || '',
    country: user?.country || '',
    bio: user?.bio || '',
    website: user?.website || '',
    orcid: user?.orcid || ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await updateProfile(profileData);
    
    if (result.success) {
      setSuccess('Profil mis à jour avec succès !');
      setTimeout(() => {
        setSuccess('');
      }, 3000);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Mon Profil</DialogTitle>
          <DialogDescription>
            Gérez vos informations personnelles et préférences.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="profile-name">Nom complet</Label>
            <Input
              id="profile-name"
              value={profileData.name}
              onChange={(e) => setProfileData(prev => ({ ...prev, name: e.target.value }))}
            />
          </div>
          
          <div>
            <Label htmlFor="profile-institution">Institution</Label>
            <Input
              id="profile-institution"
              value={profileData.institution}
              onChange={(e) => setProfileData(prev => ({ ...prev, institution: e.target.value }))}
            />
          </div>
          
          <div>
            <Label htmlFor="profile-country">Pays</Label>
            <Input
              id="profile-country"
              value={profileData.country}
              onChange={(e) => setProfileData(prev => ({ ...prev, country: e.target.value }))}
            />
          </div>
          
          <div>
            <Label htmlFor="profile-orcid">ORCID ID</Label>
            <Input
              id="profile-orcid"
              value={profileData.orcid}
              onChange={(e) => setProfileData(prev => ({ ...prev, orcid: e.target.value }))}
              placeholder="0000-0000-0000-0000"
            />
          </div>
          
          <div>
            <Label htmlFor="profile-website">Site web</Label>
            <Input
              id="profile-website"
              type="url"
              value={profileData.website}
              onChange={(e) => setProfileData(prev => ({ ...prev, website: e.target.value }))}
              placeholder="https://..."
            />
          </div>
          
          <div>
            <Label htmlFor="profile-bio">Biographie</Label>
            <Textarea
              id="profile-bio"
              value={profileData.bio}
              onChange={(e) => setProfileData(prev => ({ ...prev, bio: e.target.value }))}
              rows={3}
              placeholder="Décrivez brièvement votre parcours académique..."
            />
          </div>
          
          <div className="flex justify-between pt-4">
            <div className="text-sm text-gray-500">
              <p>Email: {user?.email}</p>
              <p>Rôle: {user?.role}</p>
              <p>Membre depuis: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</p>
            </div>
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={loading} className="flex-1">
              {loading ? 'Mise à jour...' : 'Mettre à jour'}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// Thesis Claim Modal
export const ThesisClaimModal = ({ isOpen, onClose, thesis }) => {
  const { claimThesis, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [claimData, setClaimData] = useState({
    claimType: 'ownership',
    message: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setError('Vous devez être connecté pour revendiquer une thèse');
      return;
    }

    setLoading(true);
    setError('');

    const result = await claimThesis(thesis.id, claimData.claimType, claimData.message);
    
    if (result.success) {
      setSuccess('Revendication soumise avec succès ! Elle sera examinée par nos équipes.');
      setTimeout(() => {
        onClose();
      }, 2000);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Revendiquer cette thèse</DialogTitle>
          <DialogDescription>
            {thesis?.title}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="claim-type">Type de revendication</Label>
            <Select value={claimData.claimType} onValueChange={(value) => setClaimData(prev => ({ ...prev, claimType: value }))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ownership">Je suis l'auteur de cette thèse</SelectItem>
                <SelectItem value="correction">Correction des métadonnées</SelectItem>
                <SelectItem value="supervisor">Je suis directeur de thèse</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label htmlFor="claim-message">Message (optionnel)</Label>
            <Textarea
              id="claim-message"
              value={claimData.message}
              onChange={(e) => setClaimData(prev => ({ ...prev, message: e.target.value }))}
              rows={3}
              placeholder="Informations complémentaires..."
            />
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={loading} className="flex-1">
              {loading ? 'Envoi...' : 'Soumettre la revendication'}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// Thesis Report Modal
export const ThesisReportModal = ({ isOpen, onClose, thesis }) => {
  const { reportThesis } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [reportData, setReportData] = useState({
    reportType: 'copyright',
    description: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await reportThesis(thesis.id, reportData.reportType, reportData.description);
    
    if (result.success) {
      setSuccess('Signalement envoyé avec succès ! Il sera examiné par nos équipes.');
      setTimeout(() => {
        onClose();
      }, 2000);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Signaler cette thèse</DialogTitle>
          <DialogDescription>
            {thesis?.title}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="report-type">Type de problème</Label>
            <Select value={reportData.reportType} onValueChange={(value) => setReportData(prev => ({ ...prev, reportType: value }))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="copyright">Violation de droits d'auteur</SelectItem>
                <SelectItem value="metadata_error">Erreur dans les métadonnées</SelectItem>
                <SelectItem value="inappropriate_content">Contenu inapproprié</SelectItem>
                <SelectItem value="duplicate">Doublon</SelectItem>
                <SelectItem value="other">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label htmlFor="report-description">Description du problème</Label>
            <Textarea
              id="report-description"
              value={reportData.description}
              onChange={(e) => setReportData(prev => ({ ...prev, description: e.target.value }))}
              rows={4}
              placeholder="Décrivez le problème en détail..."
              required
            />
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={loading} className="flex-1">
              {loading ? 'Envoi...' : 'Envoyer le signalement'}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};