# Godot 4.7.2 — Kalıcı GitHub Actions Oyun Projesi

Bu sistem Unity olmadan, **normal GitHub-hosted Ubuntu** runner'larında çalışan açık kaynak Godot 4.7.2 tabanlı bir oyun projesi oluşturur, çalıştırır ve sonuçları başka bir Git dalına kaydeder.

## Dallar / dosyalar

| Yol | Görevi |
|---|---|
| [gui-computer-use-20261023](../../tree/gui-computer-use-20261023) | Sistem kodu, CI iş akışı ve ilk proje şablonu |
| [godot-persistent-state](../../tree/godot-persistent-state) | Çalıştırmalar arasında **kalıcı oyun projesi**, loglar, ekran görüntüleri |
| `godot/` (kod dalında) | Yalnızca **ilk kurulum** için başlangıç oyunu |
| `persistent/project/` (durum dalında) | Artık asıl oyun projesi; yeni CI burada kalan son sürümden devam eder |
| `persistent/run-history/N/` (durum dalında) | N'inci çalıştırmanın logları, test durumu ve dosya özeti |

Workflow: [Godot persistent builder](../../actions/workflows/godot-persistent.yml). `gui-computer-use-20261023` dalındaki `.github/workflows/godot-persistent.yml` dosyasında.

## Nasıl çalışıyor?

1. Kaynak dalı ve durum dalı iki ayrı klasöre checkout edilir.
2. Eğer durum dalında `persistent/project/project.godot` varsa **oradaki tüm oyun projesi** geri yüklenir. Yoksa `godot/` başlangıç şablonu kopyalanır.
3. `data/ci_state.json` içindeki önceki çalıştırma numarası okunur ve 1 artırılır. Böylece önceki üretimin gerçekten kullanıldığını ölçüyoruz.
4. Godot 4.7.2 kurulur, sahneler import edilir ve oyun `--headless` modunda gerçekten çalıştırılır.
5. İsteğe bağlı yazılımsal OpenGL pencere ekran görüntüsü alınır.
6. Başarılı testten sonra **oyun dosyaları** `persistent/project/` içine kaydedilir; her koşulda **çalıştırma logları** `persistent/run-history/N/` altına commit edilir.
7. Runner sıfırlansa da sonraki çalıştırmada bu kayıtlar Git'ten geri alınır. Proje kırılırsa son çalışan oyun projesi korunur.

## Yeni oyunu nerede geliştireceğiz?

**İlk çalıştırmadan sonra** Godot sahnelerini, GDScript dosyalarını, materyalleri, modelleri ve resursları `godot-persistent-state:persistent/project/` altında düzenlemek gerekir; yeni CI orayı yetkili kaynak olarak kullanır. Başlangıç şablonu ancak `persistent/project/` bulunamazsa kullanılır.

İlk örnek, 3D zeminde hareket edebildiğin ve enerji bloklarını toplayabildiğin bir sahne içerir. Ok tuşları veya WASD (Godot varsayılan tuş eşlemeleri) kullanılır. Temel görünüm gerçek Godot motorunda oluşturulur.

## Yeniden çalıştırma

Kod dalındaki `godot/**` veya `automation/godot/**` değişiklikleri `push` üzerinde otomatik test başlatır. Önceki çalışmanın GitHub Actions sayfasındaki **Re-run all jobs** seçeneği de kalıcı durum dalını tekrar kontrol ederek yeni bir çalışma başlatır.

GitHub'da iş akışı **Run workflow** düğmesinin görünebilmesi için iş akışının ayrıca varsayılan (`main`) dalda bulunması gerekebilir. Bu nedenle yalnızca deney dalındaki workflow'a güvenerek manuel `workflow_dispatch` kullanılacağı varsayılmaz.

## Önemli sınırlar

- Godot ücretsiz ve MIT lisanslıdır. Unity lisansı, Unity Hub girişi veya Unity Cloud servisi kullanılmaz.
- Ücretsiz **herkese açık repo** üzerindeki standart GitHub-hosted runner'larda faturalandırılan dakika yoktur, ancak koşucu çalışma süresi, eşzamanlı iş, disk, ağ ve GitHub kötüye kullanım sınırları geçerlidir.
- `.godot` önbelleği ve geçici dosyalar kalıcı Git durumuna kaydedilmez; projenin kaynak varlıkları ve üretilen küçük çıktıları kaydedilir.
- GitHub'ın normal Git'e tek dosya yükleme sınırı **100 MiB**'dir. Büyük modeller/videolar için Git LFS, GitHub Releases veya harici depolama gerekir. Sistem 95 MiB'den büyük dosyaları Git'e pushlamaz.
- Çalıştırma geçmişi branch commit'leriyle büyür. Büyük veri sürümleri için temizleme politikası veya ayrı artifact/depolama gerekir.
- Game GUI screenshot saf yazılım OpenGL kullandığından düşük performans veya hata gösterebilir. Headless oyunun çalışması asıl zorunlu testtir.

## Yerel Godot

Godot 4.7.2'yi aç ve durum dalından `persistent/project/` klasörünü indirip `project.godot` dosyasını içe aktar. Varsayılan sahneyi F6/F5 ile çalıştır.
