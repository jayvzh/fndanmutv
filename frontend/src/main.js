import { createApp } from 'vue'
import App from './App.vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import { zhHans } from 'vuetify/locale'

const vuetify = createVuetify({
  components,
  directives,
  // 中文语言包：表格 footer「每页数目：」「全部」等 Vuetify 内置文案中文化
  locale: {
    locale: 'zhHans',
    messages: { zhHans },
  },
  defaults: {
    VBtn: {
      rounded: 'lg',
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FB8C00',
          background: '#F5F7FA',
          surface: '#FFFFFF',
        },
      },
    },
  },
})

const app = createApp(App)
app.use(vuetify)
app.mount('#app')
