
using UnityEngine;

namespace PVSimulator
{
    public class CameraController : MonoBehaviour
    {
        [Header("Ŀ������")]
        [SerializeField] private Transform target;
        [SerializeField] private float initialDistance = 50f;

        [Header("��ת����")]
        [SerializeField] private float rotationSpeed = 2f;
        [SerializeField] private float minVerticalAngle = 5f;
        [SerializeField] private float maxVerticalAngle = 85f;

        [Header("��������")]
        [SerializeField] private float zoomSpeed = 5f;
        [SerializeField] private float minDistance = 5f;
        [SerializeField] private float maxDistance = 300f;

        [Header("ƽ������")]
        [SerializeField] private float panSpeed = 0.3f;

        private float currentDistance;
        private float currentHorizontalAngle;
        private float currentVerticalAngle;

        void Start()
        {
            if (target == null)
            {
                GameObject go = new GameObject("CameraTarget");
                go.transform.position = Vector3.zero;
                target = go.transform;
            }

            currentDistance = initialDistance;
            currentHorizontalAngle = 0f;
            currentVerticalAngle = 45f;

            UpdateCameraPosition();
        }

        void Update()
        {
            //Debug.Log($"Mouse X: {Input.GetAxis("Mouse X")}, Mouse Y: {Input.GetAxis("Mouse Y")}");
            bool changed = false;

            // �����ק��ת
            if (Input.GetMouseButton(0))
            {
                float mouseX = Input.GetAxis("Mouse X") * rotationSpeed;
                float mouseY = Input.GetAxis("Mouse Y") * rotationSpeed;

                currentHorizontalAngle += mouseX;
                currentVerticalAngle -= mouseY;
                currentVerticalAngle = Mathf.Clamp(currentVerticalAngle, minVerticalAngle, maxVerticalAngle);
                changed = true;
            }

            // ��������
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (scroll != 0)
            {
                currentDistance -= scroll * zoomSpeed * currentDistance * 0.1f;
                currentDistance = Mathf.Clamp(currentDistance, minDistance, maxDistance);
                changed = true;
            }

            // �Ҽ���קƽ��
            if (Input.GetMouseButton(1))
            {
                float mouseX = Input.GetAxis("Mouse X") * panSpeed;
                float mouseY = Input.GetAxis("Mouse Y") * panSpeed;

                Vector3 right = transform.right;
                Vector3 forward = Vector3.Cross(Vector3.up, right).normalized;

                target.position -= right * mouseX + forward * mouseY;
                changed = true;
            }

            if (changed)
            {
                UpdateCameraPosition();
            }
        }

        private void UpdateCameraPosition()
        {
            if (target == null) return;

            float h = currentHorizontalAngle * Mathf.Deg2Rad;
            float v = currentVerticalAngle * Mathf.Deg2Rad;

            float x = Mathf.Sin(h) * Mathf.Cos(v) * currentDistance;
            float y = Mathf.Sin(v) * currentDistance;
            float z = Mathf.Cos(h) * Mathf.Cos(v) * currentDistance;

            transform.position = target.position + new Vector3(x, y, z);
            transform.LookAt(target);
        }

        public void SetTargetPosition(Vector3 position)
        {
            if (target != null)
            {
                target.position = position;
                UpdateCameraPosition();
            }
        }

        public void SetDistance(float distance)
        {
            currentDistance = Mathf.Clamp(distance, minDistance, maxDistance);
            UpdateCameraPosition();
        }
    }
}
