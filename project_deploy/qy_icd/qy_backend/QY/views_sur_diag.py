from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from .models import V_Patient_Surgery, V_Patient_Diagnosis

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_icd_codes(request):
    """
    POST: 批量保存诊断和手术编码结果
    Expected Data Format:
    [
        {
            "answerType": "surgery",
            "case_id": "...",
            "seq": 1,
            "name": "...",
            "code": "...",
            "model_response_time": "2023-10-27T10:00:00Z"
        },
        {
            "answerType": "diagnosis",
            "case_id": "...",
            "seq": 1,
            "diag_type": "出院诊断",
            "name": "...",
            "code": "...",
            "model_response_time": "..."
        }
    ]
    """
    data = request.data
    if not isinstance(data, list):
        return JsonResponse({"code": 400, "msg": "Data format error, list expected"}, status=400)

    surgery_list = []
    diagnosis_list = []

    try:
        with transaction.atomic():
            for entry in data:
                answer_type = entry.get('answerType')
                case_id = entry.get('case_id')
                name = entry.get('name')
                code = entry.get('code')
                seq = entry.get('seq')
                response_time = entry.get('model_response_time')

                if not all([answer_type, case_id, name, code]):
                    continue  # Skip incomplete entries

                # Parse time string to datetime object if necessary, 
                # strictly Django handles ISO strings well, but being explicit is safe
                # If response_time is None, it will remain None or use auto_now if configured (we set null=True)
                
                if answer_type == 'surgery':
                    surgery_list.append(V_Patient_Surgery(
                        case_id=case_id,
                        surgery_seq=seq,
                        surgery_code=code,
                        surgery_name=name,
                        model_response_time=response_time
                    ))
                
                elif answer_type == 'diagnosis':
                    diag_type = entry.get('diag_type', '出院诊断') # Default or extracted
                    diagnosis_list.append(V_Patient_Diagnosis(
                        case_id=case_id,
                        diag_type=diag_type,
                        diag_seq=seq,
                        diag_code=code,
                        diag_name=name,
                        model_response_time=response_time
                    ))

            # Bulk Create
            if surgery_list:
                V_Patient_Surgery.objects.bulk_create(surgery_list)
            
            if diagnosis_list:
                V_Patient_Diagnosis.objects.bulk_create(diagnosis_list)
        
        if (len(diagnosis_list) + len(surgery_list)) == 0:
            return JsonResponse({"code": 400, "msg": "No valid data to save"}, status=400)
        
        return JsonResponse({
            "code": 200, 
            "msg": f"保存成功! 诊断: {len(diagnosis_list)} 条, 手术: {len(surgery_list)} 条"
        })

    except Exception as e:
        print(f"Error saving ICD codes: {str(e)}")
        return JsonResponse({"code": 500, "msg": "保存失败，服务器内部错误"}, status=500)