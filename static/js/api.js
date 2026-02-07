/**
 * CertifyHub API Client
 * Wrapper for backend API communication
 */

const API = {
    // Base URL (adjust if needed)
    baseURL: window.location.origin,
    
    // Get stored JWT token
    getToken() {
        return (
            localStorage.getItem('token') ||
            localStorage.getItem('access_token') ||
            sessionStorage.getItem('token') ||
            sessionStorage.getItem('access_token')
        );
    },
    
    // Set JWT token
    setToken(token) {
        localStorage.setItem('token', token);
    },
    
    // Clear token (logout)
    clearToken() {
        localStorage.removeItem('token');
    },
    
    // Generic fetch wrapper
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = this.getToken();
        
        const defaultHeaders = {};
        
        // Only set Content-Type if not FormData (FormData handles its own Content-Type)
        if (!(options.body instanceof FormData)) {
            defaultHeaders['Content-Type'] = 'application/json';
        }
        
        if (token) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            headers: { ...defaultHeaders, ...options.headers },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            // Handle 401 unauthorized
            if (response.status === 401) {
                this.clearToken();
                window.location.href = '/login';
                return null;
            }
            
            // Parse response
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else if (response.status === 204) {
                data = null;
            } else {
                data = await response.text();
            }
            
            return {
                ok: response.ok,
                status: response.status,
                data: data
            };
        } catch (error) {
            console.error('API request failed:', error);
            return {
                ok: false,
                status: 0,
                error: error.message
            };
        }
    },
    
    // Authentication APIs
    auth: {
        async login(email, password) {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);
            
            return API.request('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: formData.toString()
            });
        },
        
        async logout() {
            const result = await API.request('/auth/logout', { method: 'POST' });
            API.clearToken();
            return result;
        },
        
        async changePassword(currentPassword, newPassword) {
            return API.request('/auth/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });
        }
    },
    
    // Club Admin APIs
    admin: {
        async getDashboard() {
            return API.request('/admin/dashboard');
        },
        
        async getActivityLogs(limit = 10, offset = 0, action = null, days = 7) {
            let url = `/admin/activity-logs?limit=${limit}&offset=${offset}&days=${days}`;
            if (action) {
                url += `&action=${action}`;
            }
            return API.request(url);
        },
        
        async getActivityStats(days = 7) {
            return API.request(`/admin/activity-stats?days=${days}`);
        },
        
        // Template APIs
        async getTemplates() {
            return API.request('/admin/templates');
        },
        
        async getTemplate(templateId) {
            return API.request(`/admin/templates/${templateId}`);
        },
        
        async createTemplate(name, imageData, textFields, audience = 'student') {
            const formData = new FormData();
            formData.append('template_name', name);
            formData.append('audience', audience);
            formData.append('image', imageData);
            formData.append('text_fields', JSON.stringify(textFields));
            
            const token = API.getToken();
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            
            return API.request('/admin/templates/upload', {
                method: 'POST',
                headers: headers,
                body: formData
            });
        },
        
        async updateTemplate(templateId, name, imageData = null, textFields) {
            const formData = new FormData();
            formData.append('name', name);
            if (imageData) {
                formData.append('image', imageData);
            }
            formData.append('text_fields', JSON.stringify(textFields));
            
            return API.request(`/admin/templates/${templateId}`, {
                method: 'PUT',
                headers: {},
                body: formData
            });
        },

        async updateTemplateCoordinates(templateId, textFields) {
            return API.request(`/admin/templates/${templateId}/coordinates`, {
                method: 'PUT',
                body: JSON.stringify({
                    text_fields: textFields
                })
            });
        },
        
        async deleteTemplate(templateId) {
            return API.request(`/admin/templates/${templateId}`, {
                method: 'DELETE'
            });
        },
        
        // Attendee APIs
        async getAttendees() {
            return API.request('/admin/attendees');
        },
        
        async getAttendee(attendeeId) {
            return API.request(`/admin/attendees/${attendeeId}`);
        },
        
        async uploadAttendees(csvFile, role = 'student') {
            const formData = new FormData();
            formData.append('file', csvFile);
            formData.append('role', role);
            
            return API.request('/admin/attendees/upload-file', {
                method: 'POST',
                headers: {},
                body: formData
            });
        },
        
        // Certificate APIs
        async generateCertificate(attendeeId, templateId) {
            return API.request('/admin/certificates', {
                method: 'POST',
                body: JSON.stringify({
                    attendee_id: attendeeId,
                    template_id: templateId
                })
            });
        },
        
        async getCertificates(status = null) {
            let url = '/admin/certificates';
            if (status) {
                url += `?status=${status}`;
            }
            return API.request(url);
        }
    },
    
    // Public APIs (no authentication required)
    public: {
        async verifyCertificate(certificateId) {
            return API.request(`/certificates/verify/${certificateId}`);
        },
        
        async downloadCertificate(attendeeId, token = null) {
            const url = `/certificates/download/${attendeeId}${token ? `?token=${token}` : ''}`;
            window.location.href = url;
        }
    }
};

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
