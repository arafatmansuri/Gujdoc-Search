import { configureStore, createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import type { TypedUseSelectorHook } from 'react-redux'
import type { DocumentRecord } from './api'
import { api, getApiError } from './api'

type DocumentsState = {
  items: DocumentRecord[]
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  error: string | null
  invalidated: boolean
}

const initialState: DocumentsState = {
  items: [],
  status: 'idle',
  error: null,
  invalidated: false,
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
      return state.documents.status !== 'loading'
        && (state.documents.status !== 'succeeded' || state.documents.invalidated)
    },
  },
)

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {
    invalidateDocuments(state) {
      state.invalidated = true
      state.status = 'idle'
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
        state.invalidated = false
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload ?? 'Could not load your documents. Please try again.'
      })
  },
})

export const { invalidateDocuments } = documentsSlice.actions

export const store = configureStore({
  reducer: {
    documents: documentsSlice.reducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Keep the typed hooks local to the app so components cannot accidentally use an untyped store.
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
