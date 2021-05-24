using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// <c>CartGame</c> Creates cars and manages the state of the race.
/// </summary>
public class CartGame : MonoBehaviour
{
    [Tooltip("The track upon which to race.")]
    public SplineTrack track;
    [Tooltip("The car prefab to instantiate at the start of the game.")]
    public CarController carPrefab;
    [Tooltip("The chase camera prefab to instantiate at the start of the game.")]
    public CarCamera cameraPrefab;

    private CarController car;
    private CarCamera chaseCamera;
    private int nextCheckpointIndex;

    void Start()
    {
        if (track && carPrefab && cameraPrefab) {
            if (Camera.main) {
                Camera.main.gameObject.SetActive(false);
            }
            Transform[] controlPoints = track.GetControlPoints();
            Transform startingPoint = controlPoints[0];
            car = GameObject.Instantiate(carPrefab, startingPoint.position, startingPoint.rotation);
            chaseCamera = GameObject.Instantiate(cameraPrefab, startingPoint.position,
                startingPoint.rotation);
            chaseCamera.target = car.GetComponent<Rigidbody>();
            nextCheckpointIndex = 1;
        } else {
            Debug.Log("CartGame is not configured properly. Please set a track, car, and camera.");
        }
    }

    void Update() {
        if (track && car) {
            Transform[] controlPoints = track.GetControlPoints();
            Transform checkpoint = controlPoints[nextCheckpointIndex];
            Vector3 carToCheckpoint = (car.transform.position - checkpoint.position).normalized;
            if(Vector3.Dot(checkpoint.forward, carToCheckpoint) > 0) {
                ++nextCheckpointIndex;
                if (nextCheckpointIndex >= controlPoints.Length) {
                    nextCheckpointIndex = 0;
                    Debug.Log("Completed a lap!");
                }
            }
        }
    }
}
