# LIMS Frontend

React frontend for the Laboratory Information Management System (LIMS) MVP.

## Features

### Sample Accessioning (US-1)
- Multi-step wizard for sample entry
- Required fields: due_date, received_date, sample_type, status, matrix, temperature
- Optional double-entry validation for key fields
- Test assignment during accessioning
- Container assignment with concentration/amount tracking

### Container Management (US-5)
- Create and manage hierarchical containers
- Support for different container types (tube, plate, well, rack)
- Contents linking with concentration/amount/units
- Pooled samples support with calculations

### Test Assignment (US-7)
- Assign analyses to samples during accessioning
- Test instances with status tracking
- Integration with sample lifecycle

### Dashboard
- Role-based views (client sees own projects)
- Sample listing with filtering by status/project
- Summary statistics
- Real-time status updates

## Technical Implementation

### Architecture
- **React 18** with TypeScript
- **Material-UI** for components and theming
- **Formik + Yup** for form management and validation
- **React Router** for navigation
- **Axios** for API communication
- **Jest + Testing Library** for testing

### State Management
- Context API for user authentication and permissions
- Local state for component-specific data
- API service layer for backend communication

### Security
- JWT token-based authentication
- Role-based access control (RBAC)
- Permission-based UI rendering
- Secure API communication

### Accessibility
- ARIA labels and semantic HTML
- Keyboard navigation support
- Screen reader compatibility
- WCAG 2.1 compliance

## Components

### Pages
- `Dashboard` - Main overview with sample listing and filtering
- `AccessioningForm` - Multi-step sample accessioning wizard
- `ContainerManagement` - Container creation and management
- `Login` - User authentication

### Accessioning Components
- `SampleDetailsStep` - Sample information entry with double-entry validation
- `TestAssignmentStep` - Analysis selection and assignment
- `ReviewStep` - Final review before submission

### Container Components
- `ContainerForm` - Container creation/editing form
- `ContainerDetails` - Container information and contents management

### Shared Components
- `Navbar` - Navigation with role-based menu items
- `UserContext` - Authentication and permission management

## API Integration

### Endpoints Used
- `POST /auth/login` - User authentication
- `GET /auth/me` - Current user information
- `GET /samples` - List samples with filtering
- `POST /samples` - Create new sample
- `PATCH /samples/{id}` - Update sample
- `GET /tests` - List tests
- `POST /tests` - Create test assignment
- `GET /containers` - List containers
- `POST /containers` - Create container
- `POST /contents` - Link sample to container
- `GET /analyses` - List available analyses
- `GET /lists/{name}/entries` - Get lookup data
- `GET /units` - Get measurement units
- `GET /projects` - Get user projects

### Error Handling
- Global error handling with user-friendly messages
- Form validation with real-time feedback
- Network error recovery
- Authentication error handling

## Testing

### Test Coverage
- Component rendering tests
- Form submission tests
- User interaction tests
- API integration tests
- Error handling tests

### Running Tests
```bash
npm test
```

### Test Structure
- Unit tests for individual components
- Integration tests for user workflows
- Mock API responses for consistent testing
- Accessibility testing with screen readers

## Development

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running on localhost:8000

### Setup
```bash
npm install
npm start
```

### Environment Variables
```env
REACT_APP_API_URL=http://localhost:8000
```

### Code Quality
- ESLint for code linting
- TypeScript for type safety
- Prettier for code formatting
- Husky for pre-commit hooks

## Deployment

### Build
```bash
npm run build
```

### Docker
The frontend is containerized with Nginx for production serving.

### Environment Configuration
- Development: `npm start`
- Production: Built files served via Nginx
- API URL configurable via environment variables

## User Workflows

### Sample Accessioning Workflow
1. Navigate to Accessioning page
2. Fill sample details (name, type, dates, etc.)
3. Enable double-entry validation if needed
4. Select analyses for testing
5. Review all information
6. Submit to create sample, container, and tests

### Container Management Workflow
1. Navigate to Containers page
2. Create new container with type and specifications
3. Add samples to container with concentration/amount
4. Manage container contents
5. Track container hierarchy

### Dashboard Workflow
1. View sample summary statistics
2. Filter samples by status/project
3. Track sample progress
4. Monitor test assignments

## Security Considerations

### Authentication
- JWT tokens stored in localStorage
- Automatic token refresh
- Secure logout with token cleanup

### Authorization
- Role-based component rendering
- Permission-based feature access
- Client data isolation

### Data Protection
- Input validation and sanitization
- XSS protection
- CSRF token handling
- Secure API communication

## Performance

### Optimization
- Code splitting for route-based loading
- Lazy loading for heavy components
- Memoization for expensive calculations
- Efficient re-rendering with React.memo

### Monitoring
- Error boundary implementation
- Performance metrics tracking
- User interaction analytics
- API response time monitoring
