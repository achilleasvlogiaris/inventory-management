<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget.title') }}</h3>
      </div>
      <div class="budget-slider-row">
        <input
          type="range"
          min="0"
          max="100000"
          step="500"
          v-model.number="budget"
        />
        <div class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.stats.itemsRecommended') }}</div>
          <div class="stat-value">{{ recommendations.length }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.stats.totalCost') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.stats.remainingBudget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ remainingBudget.toLocaleString() }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendations.length }})</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td><strong>{{ rec.sku }}</strong></td>
                <td>{{ translateProductName(rec.item_name) }}</td>
                <td>{{ rec.shortfall }}</td>
                <td>{{ rec.recommended_quantity }}</td>
                <td>{{ currencySymbol }}{{ rec.unit_cost }}</td>
                <td><strong>{{ currencySymbol }}{{ rec.line_total.toLocaleString() }}</strong></td>
              </tr>
              <tr v-if="recommendations.length === 0">
                <td colspan="6" class="empty-row">{{ t('restocking.noRecommendations') }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="place-order-row">
          <button
            class="place-order-btn"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="submitSuccess" class="success-banner">
          {{ t('restocking.orderSuccess', { orderNumber: submitSuccess.order_number, leadTime: submitSuccess.lead_time_days }) }}
        </div>
        <div v-if="submitError" class="error">{{ submitError }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(10000)
    const loading = ref(true)
    const error = ref(null)
    const recommendations = ref([])
    const totalCost = ref(0)
    const remainingBudget = ref(0)

    const submitting = ref(false)
    const submitSuccess = ref(null)
    const submitError = ref(null)

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        const data = await api.getRestockRecommendations(budget.value)
        recommendations.value = data.recommendations
        totalCost.value = data.total_cost
        remainingBudget.value = data.remaining_budget
      } catch (err) {
        error.value = 'Failed to load restock recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    let debounceTimer = null
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 400)
    })

    onBeforeUnmount(() => {
      clearTimeout(debounceTimer)
    })

    const placeOrder = async () => {
      try {
        submitting.value = true
        submitError.value = null
        submitSuccess.value = null

        const payload = {
          budget: budget.value,
          items: recommendations.value.map(rec => ({
            sku: rec.sku,
            quantity: rec.recommended_quantity
          }))
        }
        const order = await api.submitRestockOrder(payload)
        submitSuccess.value = order
      } catch (err) {
        submitError.value = 'Failed to place restock order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      translateProductName,
      budget,
      loading,
      error,
      recommendations,
      totalCost,
      remainingBudget,
      submitting,
      submitSuccess,
      submitError,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-slider-row {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

input[type="range"] {
  flex: 1;
  accent-color: #2563eb;
  height: 6px;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 140px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.place-order-row {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.938rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.success-banner {
  margin-top: 1rem;
  background: #d1fae5;
  color: #065f46;
  padding: 0.875rem 1rem;
  border-radius: 8px;
  font-size: 0.938rem;
}

.empty-row {
  text-align: center;
  color: #64748b;
  padding: 1.5rem;
}
</style>
