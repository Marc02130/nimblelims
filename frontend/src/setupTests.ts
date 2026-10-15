import '@testing-library/jest-dom';
import { TextDecoder, TextEncoder } from 'util';

// jsdom (Jest 27, react-scripts 5) has no TextEncoder/TextDecoder; MUI X v8
// (@mui/x-internals/hash) needs them at import time.
Object.assign(global, { TextEncoder, TextDecoder });

// Kept out of src/__tests__ so Jest does not collect it as an empty test suite.
import './testSetup';
