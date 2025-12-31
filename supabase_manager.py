

# import datetime
# from typing import List, Optional
# from dotenv import load_dotenv
# from supabase import create_client, Client
# import os

# from models.device_model import ArtProgressRequest, StringArtRequest



# class SupabaseService:
#     def __init__(self):
#         load_dotenv()
#         SUPABASE_URL = os.getenv("SUPABASE_URL")
#         SUPABASE_KEY = os.getenv("SUPABASE_KEY")

#         # print(f"LLLLLLLLLLLLLLLLLLLLLLLLLLLL {SUPABASE_URL} ")
        
#         if not SUPABASE_URL or not SUPABASE_KEY:
#             raise RuntimeError("Supabase credentials missing")
        
#         self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
#         self.arts = "tblArts"
#         self.devices = "tblDevices"
#         self.threads = "tblThreads"
#         self.sp: StringArtRequest = None
#         self.threadID: str =''
        
#     def getArt(self, artID: str) -> Optional[StringArtRequest]:
#         try:
#             response = (
#                 self.client
#                 .table(self.arts)
#                 .select("*")
#                 .eq("id", artID)
#                 .execute()
#             )
            
#             if not response.data:
#                 return None
            
#             # print(f">>>>>>>>>>>>>>>>>.   {response.data}")
            
#             self.sp = StringArtRequest(**response.data[0]) 
#             return self.sp
#         except Exception as e:
#             # print(f"Error fetching art: {e}")
#             return None
    
        
#     def createThread(self, data: ArtProgressRequest) -> Optional[ArtProgressRequest]:
#         try:
#             # Ensure artID is set from self.sp if not provided
#             if not data.artID and self.sp:
#                 data.artID = self.sp.id
            
#             _temp = data.model_dump()
#             _temp.pop('id', None)  # Remove id if present
            
#             response = (
#                 self.client.table(self.threads)
#                 .insert(_temp)
#                 .execute()
#             )

#             # print(response)
            
#             if not response.data:
#                 return None
            
#             res = ArtProgressRequest(**response.data[0]) 
#             self.threadID = res.id
#             return res
#         except Exception as e:
#             # print(f"Error creating thread: {e}")
#             return None
        
#     def completeArt(self, data: List[int], total: int, img: str, nails: List) -> Optional[dict]:
#         try:
#             if not self.sp:
#                 raise ValueError("No art object loaded")
            
#             response = (
#                 self.client.table(self.arts)
#                 .update({
#                     'threads': data,
#                     'totalThreads': total,
#                     'outputImage': img,
#                     'nails': nails,
#                     # 'status': 'completed'
#                 })
#                 .eq("id", self.sp.id)
#                 .execute()
#             )

#             # print(response)
            
#             if not response.data:
#                 return None
          
#             return response.data[0]
#         except Exception as e:
#             # print(f"Error completing art: {e}")
#             return None
        
#     def uploadOutputImg(self, file: bytes) -> str:
#         try:
#             if not self.sp:
#                 raise ValueError("No art object loaded")
            
#             timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#             file_path = f'{self.sp.userID}/{timestamp}.png'

#             response = self.client.storage.from_('StringArts').upload(
#                 path=file_path,
#                 file=file,
#                 file_options={
#                     "content-type": "image/png",
#                     "upsert": "false"
#                 }
#             )
            
#             return file_path
#         except Exception as e:
#             # print(f"Error uploading image: {e}")
#             raise
    
#     # def uploadImg(self, file: str) -> str:
#     #     try:
         
            
#     #         timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#     #         file_path = f'60695215-03cd-415f-bce9-73353a33bf9e/{timestamp}.png'

#     #         response = self.client.storage.from_('StringArts').upload(
#     #             path=file_path,
#     #             file=file,
#     #             file_options={
#     #                 "content-type": "image/png",
#     #                 "upsert": "false"
#     #             }
#     #         )
            
#     #         return file_path
#     #     except Exception as e:
#     #         print(f"Error uploading image: {e}")
#     #         raise

#     def downloadImage(self, img:str)-> bytes:
#         try:
#             response = self.client.storage.from_('StringArts').download(img)
#             return response
#         except Exception as e:
#             # print(f"Error uploading image: {e}")
#             raise Exception(f"Error uploading image: {e}")
#     # def getArt(self,artID: str) -> Optional[StringArtRequest]:
#     #     try:
#     #         response = (
#     #             self.client
#     #             .table(self.arts)
#     #             .select("*")
#     #             .eq("id", artID)
#     #             .execute()
#     #         )
            
#     #         if not response.data:
#     #             return None
#     #         self.sp = StringArtRequest(**response.data[0]) 

#     #         return self.sp
#     #     except Exception as e:
#     #         return None
    
        
        
#     # def createThread(self,data :ArtProgressRequest) -> ArtProgressRequest:
#     #     try:
#     #         _temp =  data.model_dump()
#     #         _temp.pop('id')
#     #         response =  (
#     #             self.client.table(self.threads)
#     #             .insert(_temp)
#     #             .execute()
#     #         )

#     #         print(response)
            
#     #         if not response.data:
#     #             return None
#     #         res = ArtProgressRequest(**response.data[0]) 
#     #         self.threadID = res.id

#     #         return  res
#     #     except Exception as e:
#     #         return None
        
#     # def completeArt(self,data :List[int],total:int,img:str,nails:List[int]) :
#     #     try:
#     #         response =  (
#     #             self.client.table(self.arts)
#     #             .update({
#     #                 'threads': data,
#     #                 'totalThreads':total,
#     #                 'outputImage': img,
#     #                 'nails':nails
#     #             })
#     #             .eq("id", self.sp.artID)
#     #             .execute()
#     #         )

#     #         print(response)
            
#     #         if not response.data:
#     #             return None
          
#     #         return  response.data[0]
#     #     except Exception as e:
#     #         return None
        
#     # def uploadOutputImg(self,file: bytes):
#     #     timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

#     #     response = self.client.storage.from_('StringArts').upload(
#     #             path=f'{self.sp.userID}/{timestamp}.png',
#     #             file=file,
#     #             file_options={
#     #                 "content-type": "image/png",
#     #                 "upsert": True
#     #             }
#     #         )
#     #     return response


        

        
    