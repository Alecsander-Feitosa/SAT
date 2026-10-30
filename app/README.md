# App SAT (Android e iOS)

Casca nativa feita com [Capacitor](https://capacitorjs.com). O app abre o site Django
de produção (`server.url` em `capacitor.config.json`). Ou seja: **tudo que for publicado
no site aparece no app na hora**, sem precisar lançar versão nova na loja.

Só é preciso gerar versão nova do app quando mudar algo nativo: ícone, nome,
permissões, plugins ou a URL.

## 1. Antes de tudo

O app abre `https://somossatapp.com.br` (`server.url` em `capacitor.config.json`). Rode:

```bash
cd app
npm install
npx cap sync
```

O `appId` (`br.com.sat.torcedor`) vira o identificador permanente nas lojas. Troque agora
se quiser outro; depois de publicado não dá mais.

## 2. Android (Windows serve)

1. Instale o [Android Studio](https://developer.android.com/studio) (já vem com Java e SDK).
2. `npx cap open android` abre o projeto. Aguarde o Gradle sincronizar.
3. Para testar: conecte o celular com depuração USB ativada e clique em ▶ Run.
4. Para publicar: **Build › Generate Signed App Bundle** (gera `.aab`). Crie a keystore
   (`.jks`) nesse assistente e **guarde-a junto com a senha em local seguro**: sem ela não
   dá para atualizar o app na Play Store.
5. Envie o `.aab` no [Google Play Console](https://play.google.com/console) (taxa única de US$ 25).

## 3. iOS (precisa de um Mac)

1. Copie a pasta `app/` para um Mac com Xcode instalado e rode `npm install && npx cap sync ios`.
2. `npx cap open ios`, escolha seu time em **Signing & Capabilities**.
3. **Product › Archive** e envie pela janela do Organizer para o App Store Connect.
4. Exige conta [Apple Developer](https://developer.apple.com/programs/) (US$ 99/ano).

Sem Mac, dá para usar um serviço de build na nuvem (Ionic Appflow, Codemagic, GitHub Actions
com runner macOS).

## Login social (Google, Apple, Facebook)

Cada botão só aparece quando as credenciais dele estão nas variáveis de ambiente do
servidor (Render). Sem credencial, o botão fica escondido; não existe botão quebrado.

| Onde | Google | Apple | Facebook |
|---|---|---|---|
| Site | ✅ | ✅ | ✅ |
| App iPhone | ✅ nativo | ✅ nativo | — (ver abaixo) |
| App Android | ✅ nativo | — (Apple só é exigido no iOS) | — (ver abaixo) |

Dentro do app o login usa a conta do próprio aparelho (o Google bloqueia login em WebView),
e o token é trocado por uma sessão no Django em `/_allauth/browser/v1/auth/provider/token`.
Conta nova passa pela Etapa 2 (time e torcida), igual ao cadastro normal.

### Google — [console.cloud.google.com](https://console.cloud.google.com/apis/credentials)

Crie 3 IDs do cliente OAuth no mesmo projeto:

1. **Aplicativo da Web**: URI de redirecionamento
   `https://somossatapp.com.br/accounts/google/login/callback/`
   → `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`
2. **iOS**: Bundle ID `br.com.sat.torcedor` → `GOOGLE_IOS_CLIENT_ID`.
   No Xcode, em **App › Info › URL Types**, adicione um URL Scheme com o "ID do cliente
   invertido" (`com.googleusercontent.apps.XXXX`), mostrado na tela desse cliente.
3. **Android**: pacote `br.com.sat.torcedor` + impressão digital SHA-1 da keystore de
   release (e da de debug, para testar). Não vira variável de ambiente; o Google só valida.
   Se publicar pela Play Store com "Assinatura de apps do Google Play", cadastre também o
   SHA-1 que aparece no Play Console.

### Apple — [developer.apple.com](https://developer.apple.com/account/resources)

1. **Identifiers › App IDs**: `br.com.sat.torcedor` com "Sign in with Apple" marcado
   (a capability já está ligada no projeto iOS: `App.entitlements`).
2. **Identifiers › Services IDs**: crie um (ex.: `br.com.sat.web`), ative Sign in with Apple,
   domínio `somossatapp.com.br`, retorno
   `https://somossatapp.com.br/accounts/apple/login/callback/` → `APPLE_SERVICES_ID`
3. **Keys**: crie uma chave com Sign in with Apple, baixe o `.p8` → `APPLE_KEY_ID`
   e `APPLE_PRIVATE_KEY` (conteúdo do arquivo; no Render pode colar com as quebras de linha).
4. `APPLE_TEAM_ID`: canto superior direito da conta de desenvolvedor.

### Facebook — [developers.facebook.com](https://developers.facebook.com/apps)

Crie um app do tipo Consumidor com o produto "Login do Facebook", URI de redirecionamento
`https://somossatapp.com.br/accounts/facebook/login/callback/` → `FACEBOOK_APP_ID` e
`FACEBOOK_APP_SECRET`. Isso liga o botão **no site**.

Nos apps, o SDK do Facebook exige o App ID gravado nos arquivos nativos antes do build,
por isso está desligado (`"facebook": false` em `capacitor.config.json`). Com o App ID em
mãos dá para ativar seguindo a seção Facebook do README do plugin
(`node_modules/@capgo/capacitor-social-login/README.md`).

### Variáveis no Render

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_IOS_CLIENT_ID=...
APPLE_SERVICES_ID=br.com.sat.web
APPLE_TEAM_ID=...
APPLE_KEY_ID=...
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----...
FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
```

Se algum provedor já tiver sido cadastrado no admin do Django (Social applications),
apague o cadastro de lá para não ficar duplicado com o das variáveis.

## Ícones e splash

Gerados a partir de `static/img/logo-shield.png`, com fundo `#1A1A1A`. Se o logo mudar,
substitua os PNGs em `android/app/src/main/res/mipmap-*`, `drawable*/splash.png` e
`ios/App/App/Assets.xcassets/`.

## Detectar o app no Django

O app adiciona `SATApp` ao user-agent:

```django
{% if 'SATApp' in request.META.HTTP_USER_AGENT %} ... só no app ... {% endif %}
```
