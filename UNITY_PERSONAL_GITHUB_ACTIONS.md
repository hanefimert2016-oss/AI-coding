# Unity Personal + normal GitHub Actions (tam otomatik build)

## Amaç ve sınır
- GitHub'ın **standart** `ubuntu-24.04` runner'ı workflow'u çalıştırır.
- Unity Editor ve Personal lisansı **Unity Build Automation'ın yönetilen bulut builder'ında** çalışır. GitHub runner'a Unity kurulup etkinleştirilmez; ortada self-hosted runner yoktur.
- Bir kez Unity Cloud projesi, kaynak kontrol ve servis hesabı ayarlandıktan sonra Unity projesindeki commit'ler workflow'u tetikler. Google/Unity parolası veya yerel `UnityEntitlementLicense.xml` gerekmez.
- Kullanım Unity DevOps ücretsiz kota ve sözleşme şartlarına bağlıdır. Ücretsiz kota bitince kendiliğinden ücretli hesaba geçmeyin.
- Bu workflow'un GitHub'da başlaması, kaynak Unity projesi ve Unity Cloud bağlantısı kurulmadan başarılı build anlamına gelmez.

## Bir seferlik kurulum
1. Unity Dashboard: https://cloud.unity.com — Google ile giriş yap ve bir Unity Cloud projesi aç.
2. **DevOps > Build Automation** hizmetini etkinleştir. Kullanım limitini ücretsiz kota içinde tut.
3. Source Control / repository ayarlarından `hanefimert2016-oss/AI-coding` GitHub reposunu (gerekli read izniyle) bağla.
4. `gui-computer-use-20261023` branch'i için Linux veya Windows (planda desteklenen ücretsiz makine) bir Build Target oluştur; Unity Editor sürümü ile `ProjectSettings/ProjectVersion.txt` uyuşmalı. Projeyi gerçekten derlemek için `Assets/` ve `Packages/manifest.json` gibi Unity proje dosyalarını repoya ekle.
5. Unity Cloud Dashboard > Administration > Service Accounts: hesap oluştur. Unity Build Automation'ı başlatma hakkı veren en dar proje rolünü ata ve API key (Key ID + Secret Key) oluştur.
6. GitHub repo Settings > Secrets and variables > Actions bölümünde şu beş secret'ı tanımla:
   - `UNITY_ORG_ID`: Unity Organization ID
   - `UNITY_PROJECT_ID`: Unity Cloud / Build Automation proje ID
   - `UNITY_BUILD_TARGET_ID`: oluşturulan Build Target ID
   - `UNITY_SA_KEY_ID`: Unity servis hesabı Key ID
   - `UNITY_SA_SECRET_KEY`: Unity servis hesabı Secret Key

## Kullanım
- Workflow: `.github/workflows/unity-personal-cloud-build.yml`
- GitHub > Actions > **Unity Personal — automatic cloud build (GitHub hosted)** > Run workflow, test branch'i seç.
- Unity projesinde `Assets/**`, `Packages/**`, `ProjectSettings/**` değişip pushlandığında otomatik tetiklenir.
- GitHub Actions, Build Automation API v2 üzerinden isteği yollar ve `wait_for_completion: true` ile nihai sonucu kontrol eder.
- Aynı hedefte çakışan build'leri engellemek için GitHub Actions concurrency ayarı var.

## Güvenlik
- Google/Unity şifresini GitHub'a verme; mevcut `UNITY_PASSWORD` Google şifrense sil ve Google şifreni değiştir.
- Bilgisayarındaki `UnityEntitlementLicense.xml` named-user lisansını `UNITY_LICENSE` gibi yükleme. Bu yöntem, GitHub runner'ında Personal aktivasyonunu garanti etmez.
- Service account bilgilerini kaynak kodda veya sohbet içinde paylaşma. Yalnızca GitHub Actions Secrets'a gir.
- Workflow kodu test branch'inde tutulur; ana dal değiştirilmez.

## Test sonuçları
- `Unity Personal GitHub runner activation experiment`: XML secret yok; gerçek Personal aktivasyonu doğrulanmadı.
- `Unity Personal — automatic cloud build (GitHub hosted)`: GitHub runner başladı; beş Unity Cloud secret yok; bu nedenle derleme yapılmadı.

Resmî Unity dökümanı: https://docs.unity.com/en-us/build-automation
Unity DevOps 2026 ücretsiz kullanım: https://unity.com/products/pricing-updates
