# 관광 특화 말뭉치 데이터
aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71714 -filekey 524644
aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71714 -filekey 524653



# 전시 공연 도슨트 데이터 (filekey : 441710 ~ 22)
for key in $(seq 441710 441722); do
    aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71323 -filekey $key
done


# 온라인 구어체 말뭉치 데이터

aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 625 -filekey 62288