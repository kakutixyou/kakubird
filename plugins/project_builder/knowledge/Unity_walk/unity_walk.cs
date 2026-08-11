// ---------------------------------------------------------

// // ファイル名: Gim001_StardustFootprints.cs

// // カテゴリ: Visual / 星屑の足跡

// // ---------------------------------------------------------

// using UnityEngine;

// using System.Collections;

// public class Gim001_StardustFootprints : MonoBehaviour

// {

//     [SerializeField] private GameObject stardustPrefab;

//     [SerializeField] private float disappearTime = 3.0f;



//     public void OnPlayerStep(Vector3 position)

//     {

//         // 歩いた軌跡に星屑エフェクトを生成

//         GameObject stardust = Instantiate(stardustPrefab, position, Quaternion.identity);

//         // 一定時間後に星座の形を演出して消去するコルーチンを呼ぶ

//         StartCoroutine(FormConstellationAndDestroy(stardust));

//     }



//     private IEnumerator FormConstellationAndDestroy(GameObject target)

//     {

//         yield return new WaitForSeconds(disappearTime);

//         // 星座を形成する演出（パーティクルやラインレンダラー）の処理をここに記述

//         Destroy(target);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim002_ProceduralBGM.cs

// // カテゴリ: Audio / プロシージャルBGM

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim002_ProceduralBGM : MonoBehaviour

// {

//     [SerializeField] private AudioSource[] instrumentTracks;

//     [SerializeField] private float baseTempo = 1.0f;



//     void Update()

//     {

//         // プレイヤーの歩行ペース（入力値など）を取得

//         float walkSpeed = GetPlayerWalkSpeed();

        

//         // テンポの変更と楽器トラックのフェードイン/アウト処理

//         AdjustTempoAndTracks(walkSpeed);

//     }



//     private float GetPlayerWalkSpeed() { return Input.GetAxis("Vertical"); }



//     private void AdjustTempoAndTracks(float speed)

//     {

//         foreach (var track in instrumentTracks)

//         {

//             track.pitch = baseTempo * (1.0f + speed);

//             // 速度に応じて音量(track.volume)を調整するロジックを追加

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim003_FlyingAppliances.cs

// // カテゴリ: Obstacle / 飛来する白物家電

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim003_FlyingAppliances : MonoBehaviour

// {

//     [SerializeField] private GameObject[] appliancePrefabs;

//     [SerializeField] private Transform spawnPoint;

//     [SerializeField] private float throwForce = 50f;



//     public void SpawnObstacle()

//     {

//         int index = Random.Range(0, appliancePrefabs.Length);

//         GameObject appliance = Instantiate(appliancePrefabs[index], spawnPoint.position, Random.rotation);

        

//         Rigidbody rb = appliance.GetComponent<Rigidbody>();

//         if (rb != null)

//         {

//             // プレイヤーに向かって高速で飛ばす物理演算

//             Vector3 direction = (Camera.main.transform.position - spawnPoint.position).normalized;

//             rb.AddForce(direction * throwForce, ForceMode.Impulse);

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim004_GravityInversion.cs

// // カテゴリ: Mechanic / 重力反転

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim004_GravityInversion : MonoBehaviour

// {

//     private bool isGravityInverted = false;



//     public void ToggleGravity()

//     {

//         isGravityInverted = !isGravityInverted;

        

//         // 物理演算の重力方向を反転

//         Physics.gravity = isGravityInverted ? new Vector3(0, 9.81f, 0) : new Vector3(0, -9.81f, 0);

        

//         // カメラまたはプレイヤーの天地をひっくり返す処理

//         RotatePlayerToSpace();

//     }



//     private void RotatePlayerToSpace()

//     {

//         float targetAngle = isGravityInverted ? 180f : 0f;

//         // DOTweenなどを使ってカメラを回転させる処理を推奨

//         Camera.main.transform.rotation = Quaternion.Euler(targetAngle, 0, 0);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim005_RhythmWalk.cs

// // カテゴリ: Mechanic / リズムウォーク

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim005_RhythmWalk : MonoBehaviour

// {

//     [SerializeField] private int comboCount = 0;

//     [SerializeField] private float speedMultiplier = 1.0f;



//     public void OnStepTiming(bool isPerfectTiming)

//     {

//         if (isPerfectTiming)

//         {

//             comboCount++;

//             speedMultiplier += 0.1f; // コンボで加速

//             Debug.Log($"Combo: {comboCount}! Speed: {speedMultiplier}");

//         }

//         else

//         {

//             comboCount = 0;

//             speedMultiplier = 1.0f;

//         }

//         ApplySpeedToPlayer();

//     }



//     private void ApplySpeedToPlayer() { /* プレイヤーの移動速度にspeedMultiplierを適用 */ }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim006_IndependentShadow.cs

// // カテゴリ: Surreal / 影の独立

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim006_IndependentShadow : MonoBehaviour

// {

//     [SerializeField] private GameObject shadowObject;

//     [SerializeField] private float shadowMoveSpeed = 3f;

//     private bool isDetached = false;



//     public void DetachShadow()

//     {

//         isDetached = true;

//         shadowObject.transform.SetParent(null); // 本体から切り離す

//     }



//     void Update()

//     {

//         if (isDetached)

//         {

//             // 影が勝手に前方に歩き出す

//             shadowObject.transform.position += shadowObject.transform.forward * shadowMoveSpeed * Time.deltaTime;

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim007_SpaceDistortion.cs

// // カテゴリ: Visual / 空間の歪み

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim007_SpaceDistortion : MonoBehaviour

// {

//     private Camera targetCamera;



//     void Start()

//     {

//         targetCamera = Camera.main;

//     }



//     public void DistortFOV(float targetFOV, float duration)

//     {

//         StartCoroutine(LerpFOV(targetFOV, duration));

//     }



//     private System.Collections.IEnumerator LerpFOV(float targetFOV, float duration)

//     {

//         float startFOV = targetCamera.fieldOfView;

//         float elapsed = 0f;



//         while (elapsed < duration)

//         {

//             targetCamera.fieldOfView = Mathf.Lerp(startFOV, targetFOV, elapsed / duration);

//             elapsed += Time.deltaTime;

//             yield return null;

//         }

//         targetCamera.fieldOfView = targetFOV;

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim008_MysteriousCompanion.cs

// // カテゴリ: Event / 謎の同伴者

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim008_MysteriousCompanion : MonoBehaviour

// {

//     [SerializeField] private GameObject companionPrefab;

//     private GameObject currentCompanion;



//     public void SpawnCompanion()

//     {

//         if (currentCompanion == null)

//         {

//             // プレイヤーの視界外（横や後ろ）にコッソリ生成する

//             Vector3 spawnPos = Camera.main.transform.position + Camera.main.transform.right * 2f;

//             currentCompanion = Instantiate(companionPrefab, spawnPos, Quaternion.identity);

//             Debug.Log("見知らぬオブジェクトが並走を始めた...");

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim009_HandScaleChange.cs

// // カテゴリ: Visual / 手のスケール変化

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim009_HandScaleChange : MonoBehaviour

// {

//     [SerializeField] private Transform handTransform;

//     [SerializeField] private float scaleStep = 0.05f;

//     [SerializeField] private bool grow = true;



//     public void OnStepTaken()

//     {

//         // 歩くたびにスケールを変化させる

//         float modifier = grow ? scaleStep : -scaleStep;

//         handTransform.localScale += new Vector3(modifier, modifier, modifier);

        

//         // 限界値のチェック

//         handTransform.localScale = Vector3.Max(Vector3.one * 0.1f, Vector3.Min(handTransform.localScale, Vector3.one * 10f));

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim010_CrumblingPath.cs

// // カテゴリ: Mechanic / 足元の崩落

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim010_CrumblingPath : MonoBehaviour

// {

//     [SerializeField] private float fallDelay = 0.5f;



//     private void OnTriggerExit(Collider other)

//     {

//         if (other.CompareTag("Player"))

//         {

//             // プレイヤーが通過した道（床）を一定時間後に崩落させる

//             StartCoroutine(CrumbleFloor());

//         }

//     }



//     private System.Collections.IEnumerator CrumbleFloor()

//     {

//         yield return new WaitForSeconds(fallDelay);

//         Rigidbody rb = GetComponent<Rigidbody>();

//         if(rb != null)

//         {

//             rb.isKinematic = false;

//             rb.useGravity = true;

//         }

//         // 立ち止まった際のゲームオーバー判定はPlayerコントローラー側で行う

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim011_WorldPaint.cs

// // カテゴリ: Visual / ワールドペイント

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim011_WorldPaint : MonoBehaviour

// {

//     [SerializeField] private Material worldMaterial;

//     private float colorSaturation = 0f;



//     public void OnPlayerWalk()

//     {

//         colorSaturation += 0.01f;

//         colorSaturation = Mathf.Clamp01(colorSaturation);

        

//         // シェーダーの彩度プロパティなどを更新してモノクロから鮮やかにする

//         worldMaterial.SetFloat("_Saturation", colorSaturation);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim012_ASMRSpace.cs

// // カテゴリ: Audio / ASMR空間

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim012_ASMRSpace : MonoBehaviour

// {

//     [SerializeField] private AudioClip[] asmrFootsteps; // 砂利、雪、水溜りなどの環境音

//     [SerializeField] private AudioSource earAudioSource;



//     public void PlayASMRFootstep(int terrainTypeIndex)

//     {

//         if (terrainTypeIndex >= 0 && terrainTypeIndex < asmrFootsteps.Length)

//         {

//             earAudioSource.PlayOneShot(asmrFootsteps[terrainTypeIndex]);

//             // BGMをミュートにする処理

//             // BackgroundMusicManager.Instance.MuteBGM();

//         }

//     }

// }

// // ファイル名: Gim013_TimeReversal.cs

// // カテゴリ: Mechanic / 時間の逆行

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim013_TimeReversal : MonoBehaviour

// {

//     public void CheckPlayerDirection(Vector3 moveDirection)

//     {

//         // プレイヤーが後ろ向きに歩いているか判定

//         if (Vector3.Dot(Camera.main.transform.forward, moveDirection) < -0.5f)

//         {

//             ReverseTime();

//         }

//         else

//         {

//             NormalTime();

//         }

//     }



//     private void ReverseTime()

//     {

//         // 録画したTransformの履歴を逆再生、またはパーティクルの時間を戻す処理

//         Debug.Log("時間を逆行中...");

//     }



//     private void NormalTime() { }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim014_CameraHacking.cs

// // カテゴリ: Surreal / カメラハッキング

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim014_CameraHacking : MonoBehaviour

// {

//     [SerializeField] private Camera cctvCamera;

//     [SerializeField] private Material glitchMaterial;



//     public void HackCamera()

//     {

//         // プレイヤー視点カメラを無効化し、監視カメラ視点に切り替え

//         Camera.main.enabled = false;

//         cctvCamera.enabled = true;

        

//         // 画面にグリッチや荒い画質のエフェクトを適用（PostProcessingやShaderで実装）

//         ApplyGlitchEffect();

//     }



//     private void ApplyGlitchEffect() { /* glitchMaterialを有効化 */ }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim015_KeyboardTiles.cs

// // カテゴリ: Mechanic / 鍵盤タイル

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim015_KeyboardTiles : MonoBehaviour

// {

//     [SerializeField] private AudioClip[] chords;

//     [SerializeField] private AudioSource audioSource;



//     private void OnTriggerEnter(Collider other)

//     {

//         if (other.CompareTag("PlayerFoot"))

//         {

//             // 歩幅や踏んだ位置に基づいて鳴らす和音を決定

//             int chordIndex = CalculateChordBasedOnStride();

//             audioSource.PlayOneShot(chords[chordIndex]);

//         }

//     }



//     private int CalculateChordBasedOnStride()

//     {

//         // プレイヤーの移動速度や歩幅からインデックスを計算するダミーロジック

//         return Random.Range(0, chords.Length);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim016_SpaceWhale.cs

// // カテゴリ: Event / 宇宙クジラの通過

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim016_SpaceWhale : MonoBehaviour

// {

//     [SerializeField] private Animator whaleAnimator;

//     [SerializeField] private Transform spawnPoint;



//     public void TriggerWhaleEvent()

//     {

//         // 画面を覆い尽くす巨大な宇宙クジラを目の前でゆっくり横切らせる

//         gameObject.transform.position = spawnPoint.position;

//         whaleAnimator.SetTrigger("PassThrough");

//         Debug.Log("巨大な宇宙クジラが通過します");

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim017_FakeErrorScreen.cs

// // カテゴリ: Surreal / 偽のエラー画面

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim017_FakeErrorScreen : MonoBehaviour

// {

//     [SerializeField] private GameObject bsodCanvas; // ブルースクリーンUI

//     [SerializeField] private AudioSource glitchNoise;



//     public void TriggerFakeError()

//     {

//         StartCoroutine(ShowErrorRoutine());

//     }



//     private System.Collections.IEnumerator ShowErrorRoutine()

//     {

//         glitchNoise.Play();

//         bsodCanvas.SetActive(true);

        

//         // 一瞬だけホラーテイストのバグを演出して元に戻す

//         yield return new WaitForSeconds(0.2f);

        

//         bsodCanvas.SetActive(false);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim018_PedometerMiracle.cs

// // カテゴリ: Progression / 万歩計の奇跡

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim018_PedometerMiracle : MonoBehaviour

// {

//     private int stepCount = 0;

//     [SerializeField] private int targetSteps = 1000;

//     [SerializeField] private GameObject monumentPrefab;



//     public void OnStep()

//     {

//         stepCount++;

//         if (stepCount == targetSteps)

//         {

//             TriggerMonument();

//         }

//     }



//     private void TriggerMonument()

//     {

//         // 目の前に巨大な記念碑を打ち上げる（生成する）

//         Vector3 spawnPos = Camera.main.transform.position + Camera.main.transform.forward * 10f;

//         Instantiate(monumentPrefab, spawnPos, Quaternion.identity);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim019_PhysicsBlocks.cs

// // カテゴリ: Obstacle / 道を防ぐ物理ブロック

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim019_PhysicsBlocks : MonoBehaviour

// {

//     [SerializeField] private GameObject cubePrefab;

//     [SerializeField] private int blockCount = 100;

//     [SerializeField] private Transform blockSpawnArea;



//     public void SpawnBlockade()

//     {

//         // 道を塞ぐ大量の物理キューブを生成

//         for (int i = 0; i < blockCount; i++)

//         {

//             Vector3 randomPos = blockSpawnArea.position + Random.insideUnitSphere * 3f;

//             Instantiate(cubePrefab, randomPos, Random.rotation);

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim020_KaleidoscopeWorld.cs

// // カテゴリ: Visual / 万華鏡ワールド

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim020_KaleidoscopeWorld : MonoBehaviour

// {

//     [SerializeField] private Material kaleidoscopeMaterial; // 画面反射用のポストプロセス用マテリアル



//     public void EnableKaleidoscopeEffect(bool enable)

//     {

//         // 画面が万華鏡のように反射・増殖するエフェクトのON/OFF

//         // OnRenderImage等でGraphics.Blitを使用する実装を想定

//         kaleidoscopeMaterial.SetFloat("_EffectStrength", enable ? 1.0f : 0f);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim021_StarTwinkleSync.cs

// // カテゴリ: Visual / 星の瞬きの同期

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim021_StarTwinkleSync : MonoBehaviour

// {

//     [SerializeField] private ParticleSystem starsParticle;



//     void Update()

//     {

//         // 歩幅（入力値）に応じてパーティクルのシミュレーション速度を調整

//         float walkInput = Mathf.Abs(Input.GetAxis("Vertical"));

        

//         var main = starsParticle.main;

//         // 立ち止まると宇宙全体（星の瞬き）が静止する

//         main.simulationSpeed = walkInput > 0.1f ? 1.0f : 0.0f; 

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim022_Sudden2D.cs

// // カテゴリ: Mechanic / 突然の2D化

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim022_Sudden2D : MonoBehaviour

// {

//     [SerializeField] private Camera mainCamera;

//     [SerializeField] private Transform sideViewTarget;



//     public void SwitchTo2D()

//     {

//         // カメラを真横に移動させ、正投影（Orthographic）に変更

//         mainCamera.orthographic = true;

//         mainCamera.transform.position = sideViewTarget.position;

//         mainCamera.transform.rotation = sideViewTarget.rotation;

        

//         // プレイヤーの操作入力をファミコン風の横スクロール用（X軸のみ等）に制限する処理を呼ぶ

//         Debug.Log("2D横スクロールモードに移行");

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim023_InvisibleMaze.cs

// // カテゴリ: Obstacle / 見えない迷路

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim023_InvisibleMaze : MonoBehaviour

// {

//     // MeshRendererを持たない透明なCubeオブジェクトなどを敷き詰めた迷路

//     // 衝突時のフィードバック処理

//     private void OnCollisionEnter(Collision collision)

//     {

//         if (collision.gameObject.CompareTag("Player"))

//         {

//             // 透明な壁にぶつかった際に波紋エフェクトや音を鳴らして位置を知らせる

//             PlayHitFeedback(collision.contacts[0].point);

//         }

//     }



//     private void PlayHitFeedback(Vector3 hitPoint) { /* 波紋エフェクト生成 */ }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim024_ProliferatingPlayer.cs

// // カテゴリ: Surreal / 増殖するプレイヤー

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim024_ProliferatingPlayer : MonoBehaviour

// {

//     [SerializeField] private GameObject handClonePrefab;

//     [SerializeField] private float cloneInterval = 2.0f;

//     private float timer;



//     void Update()

//     {

//         // 横移動を検知したら残像を実体化させる

//         if (Mathf.Abs(Input.GetAxis("Horizontal")) > 0.1f)

//         {

//             timer += Time.deltaTime;

//             if (timer >= cloneInterval)

//             {

//                 SpawnClone();

//                 timer = 0;

//             }

//         }

//     }



//     private void SpawnClone()

//     {

//         Instantiate(handClonePrefab, transform.position, transform.rotation);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim025_Wormhole.cs

// // カテゴリ: Event / ワープホール

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim025_Wormhole : MonoBehaviour

// {

//     [SerializeField] private Transform destinationPoint;

//     [SerializeField] private Material nextSkybox;



//     private void OnTriggerEnter(Collider other)

//     {

//         if (other.CompareTag("Player"))

//         {

//             // 全く別の色彩の宇宙（目的地）へワープ

//             other.transform.position = destinationPoint.position;

//             RenderSettings.skybox = nextSkybox;

//             Debug.Log("別の宇宙へ飛ばされました");

//         }

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim026_SpamPopups.cs

// // カテゴリ: Surreal / スパムポップアップ

// // ---------------------------------------------------------

// using UnityEngine;

// using UnityEngine.UI;



// public class Gim026_SpamPopups : MonoBehaviour

// {

//     [SerializeField] private GameObject popupPrefab;

//     [SerializeField] private Transform canvasTransform;



//     public void ShowSpam()

//     {

//         // 画面のランダムな位置に無駄な実績や広告UIを生成

//         GameObject popup = Instantiate(popupPrefab, canvasTransform);

//         RectTransform rect = popup.GetComponent<RectTransform>();

//         rect.anchoredPosition = new Vector2(Random.Range(-400, 400), Random.Range(-250, 250));

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim027_CreationMode.cs

// // カテゴリ: Visual / 天地創造モード

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim027_CreationMode : MonoBehaviour

// {

//     [SerializeField] private GameObject[] planetPrefabs;



//     public void OnStepTaken(Vector3 currentPosition)

//     {

//         // 一歩踏み出すごとに周囲に惑星や銀河をボコボコ生成

//         Vector3 randomOffset = Random.insideUnitSphere * 50f;

//         GameObject planet = Instantiate(planetPrefabs[Random.Range(0, planetPrefabs.Length)], currentPosition + randomOffset, Random.rotation);

        

//         // 飛び出してくるようなスケールアニメーション（DOTween等）を追加

//         planet.transform.localScale = Vector3.zero;

//         // planet.transform.DOScale(Vector3.one, 1f).SetEase(Ease.OutElastic);

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim028_Metamorphosis.cs

// // カテゴリ: Visual / メタモルフォーゼ

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim028_Metamorphosis : MonoBehaviour

// {

//     [SerializeField] private SkinnedMeshRenderer playerRenderer;

//     [SerializeField] private Mesh[] transformationMeshes; // 手、足、犬の顔、機械パーツ等

//     private int currentMeshIndex = 0;



//     public void TransformPlayerShape()

//     {

//         // 歩行進捗に合わせてメッシュ（またはBlendShape）をシームレスに変更

//         currentMeshIndex = (currentMeshIndex + 1) % transformationMeshes.Length;

//         playerRenderer.sharedMesh = transformationMeshes[currentMeshIndex];

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim029_HyperDash.cs

// // カテゴリ: Mechanic / ハイパーダッシュ

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim029_HyperDash : MonoBehaviour

// {

//     [SerializeField] private ParticleSystem starSpeedLines;

//     private float chargeTime = 0f;

//     private bool isDashing = false;



//     void Update()

//     {

//         // 立ち止まってチャージ

//         if (Input.GetAxis("Vertical") == 0)

//         {

//             chargeTime += Time.deltaTime;

//         }

//         else if (chargeTime > 2.0f && !isDashing) // 2秒以上溜めたらダッシュ発動

//         {

//             StartCoroutine(ExecuteDash());

//         }

//         else

//         {

//             chargeTime = 0;

//         }

//     }



//     private System.Collections.IEnumerator ExecuteDash()

//     {

//         isDashing = true;

//         starSpeedLines.Play(); // 星が線になるエフェクト

//         // 超高速移動の処理

//         yield return new WaitForSeconds(1.0f);

//         starSpeedLines.Stop();

//         isDashing = false;

//         chargeTime = 0;

//     }

// }



// // ---------------------------------------------------------

// // ファイル名: Gim030_ReturnToVoid.cs

// // カテゴリ: Event / 虚無への帰着

// // ---------------------------------------------------------

// using UnityEngine;



// public class Gim030_ReturnToVoid : MonoBehaviour

// {

//     [SerializeField] private GameObject[] allEnvironmentObjects;

//     [SerializeField] private Light directionalLight;



//     public void EnterTheVoid()

//     {

//         // すべての星と道を非表示にする

//         foreach (var obj in allEnvironmentObjects)

//         {

//             obj.SetActive(false);

//         }



//         // 完全な暗闇にする

//         directionalLight.enabled = false;

//         RenderSettings.ambientLight = Color.black;

//         RenderSettings.skybox = null; // スカイボックスを消去

        

//         Debug.Log("完全な暗闇。足音だけが響く...");

//     }