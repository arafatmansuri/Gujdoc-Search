import { configureStore, createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import type { TypedUseSelectorHook } from 'react-redux'
import type { DocumentRecord } from './api'
import { api, getApiError } from './api'

type DocumentsState = {
  items: DocumentRecord[]
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  error: string | null
}

const initialState: DocumentsState = {
  items: [],
  status: 'idle',
  error: null,
}

export const fetchDocuments = createAsyncThunk<DocumentRecord[], void, { rejectValue: string }>(
  'documents/fetch',
  async (_, { rejectWithValue }) => {
    try {
      return await api.listDocuments()
    } catch (error) {
      return rejectWithValue(getApiError(error, 'Could not load your documents. Please try again.'))
    }
  },
  {
    condition: (_, { getState }) => {
      const state = getState() as { documents: DocumentsState }
      return state.documents.status !== 'loading' && state.documents.status !== 'succeeded'
    },
  },
)

export const syncDocument = createAsyncThunk<DocumentRecord, number, { rejectValue: string }>(
  'documents/sync',
  async (id, { rejectWithValue }) => {
    try { return await api.getDocument(id) } catch (error) {
      return rejectWithValue(getApiError(error, 'Could not refresh document status.'))
    }
  },
)

type MetricsState = {
  data: Awaited<ReturnType<typeof api.metrics>> | null
  evaluation: Awaited<ReturnType<typeof api.evaluationMetrics>> | null
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  invalidated: boolean
}

const initialMetricsState: MetricsState = {
  data: null,
  evaluation: null,
  status: 'idle',
  invalidated: false,
}

export const fetchMetrics = createAsyncThunk(
  'metrics/fetch',
  async () => Promise.all([api.metrics(), api.evaluationMetrics()]),
  {
    condition: (_, { getState }) => {
      const state = getState() as { metrics: MetricsState }
      return state.metrics.status !== 'loading'
        && (state.metrics.status !== 'succeeded' || state.metrics.invalidated)
    },
  },
)

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {
    invalidateDocuments(state) {
      state.status = 'idle'
    },
    addDocument(state, action: { payload: DocumentRecord }) {
      state.items = [action.payload, ...state.items.filter((item) => item.id !== action.payload.id)]
      state.status = 'succeeded'
    },
    updateDocument(state, action: { payload: DocumentRecord }) {
      const index = state.items.findIndex((item) => item.id === action.payload.id)
      if (index >= 0) state.items[index] = action.payload
      else state.items.unshift(action.payload)
    },
    removeDocument(state, action: { payload: number }) {
      state.items = state.items.filter((item) => item.id !== action.payload)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDocuments.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.items = action.payload
        state.status = 'succeeded'
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload ?? 'Could not load your documents. Please try again.'
      })
      .addCase(syncDocument.fulfilled, (state, action) => {
        const previous = state.items.find((item) => item.id === action.payload.id)
        const finished = previous && previous.status !== action.payload.status
          && ['completed', 'failed'].includes(action.payload.status)
        const index = state.items.findIndex((item) => item.id === action.payload.id)
        if (index >= 0) state.items[index] = action.payload
        else state.items.unshift(action.payload)
        if (finished) state.status = 'succeeded'
      })
  },
})

const metricsSlice = createSlice({
  name: 'metrics',
  initialState: initialMetricsState,
  reducers: {
    invalidateMetrics(state) {
      state.invalidated = true
      state.status = 'idle'
    },
  },
  extraReducers: (builder) => builder
    .addCase(fetchMetrics.pending, (state) => { state.status = 'loading' })
    .addCase(fetchMetrics.fulfilled, (state, action) => {
      state.data = action.payload[0]
      state.evaluation = action.payload[1]
      state.status = 'succeeded'
      state.invalidated = false
    })
    .addCase(fetchMetrics.rejected, (state) => { state.status = 'failed' }),
})

export const { invalidateDocuments, addDocument, updateDocument, removeDocument } = documentsSlice.actions
export const { invalidateMetrics } = metricsSlice.actions

export const store = configureStore({
  reducer: {
    documents: documentsSlice.reducer,
    metrics: metricsSlice.reducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Keep the typed hooks local to the app so components cannot accidentally use an untyped store.
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
